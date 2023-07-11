import abc
import collections
import logging
import typing

from django.conf import settings
import elasticsearch8
from elasticsearch8.helpers import streaming_bulk

from share.search.index_strategy._base import IndexStrategy
from share.search.index_status import IndexStatus
from share.search import messages
from share.search.index_strategy.elastic_util import _timestamp_to_readable_datetime
from share.util.checksum_iri import ChecksumIri


logger = logging.getLogger(__name__)


class Elastic8IndexStrategy(IndexStrategy):
    '''abstract base class for index strategies using elasticsearch 8
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        should_sniff = settings.ELASTICSEARCH['SNIFF']
        timeout = settings.ELASTICSEARCH['TIMEOUT']
        self.es8_client = elasticsearch8.Elasticsearch(
            self.cluster_url,
            # security:
            ca_certs=self.cluster_settings.get('CERT_PATH'),
            basic_auth=self.cluster_settings.get('AUTH'),
            # retry:
            retry_on_timeout=True,
            request_timeout=timeout,
            # sniffing:
            sniff_on_start=should_sniff,
            sniff_before_requests=should_sniff,
            sniff_on_node_failure=should_sniff,
            sniff_timeout=timeout,
            min_delay_between_sniffing=timeout,
        )

    ###
    # abstract methods for subclasses to implement

    @abc.abstractmethod
    def index_settings(self):
        raise NotImplementedError

    @abc.abstractmethod
    def index_mappings(self):
        raise NotImplementedError

    @abc.abstractmethod
    def build_elastic_actions(self, messages_chunk: messages.MessagesChunk) -> typing.Iterable[tuple[int, dict]]:
        # yield (message_target_id, elastic_action) pairs
        raise NotImplementedError

    ###
    # helper methods for subclasses to use (or override)

    def build_index_action(self, doc_id, doc_source):
        return {
            '_op_type': 'index',
            '_id': str(doc_id),
            '_source': doc_source,
        }

    def build_delete_action(self, doc_id):
        return {
            '_op_type': 'delete',
            '_id': str(doc_id),
        }

    ###
    # implementation for subclasses to ignore

    # abstract method from IndexStrategy
    def compute_strategy_checksum(self):
        return ChecksumIri.digest_json(
            checksumalgorithm_name='sha-256',
            salt=self.__class__.__name__,
            raw_json={
                'settings': self.index_settings(),
                'mappings': self.index_mappings(),
            },
        )

    # abstract method from IndexStrategy
    def each_specific_index(self):
        indexname_set = set(
            self.es8_client.indices
            .get(index=self.indexname_wildcard, features=',')
            .keys()
        )
        indexname_set.add(self.current_indexname)
        for indexname in indexname_set:
            yield self.for_specific_index(indexname)

    # abstract method from IndexStrategy
    def pls_handle_messages_chunk(self, messages_chunk):
        self.assert_message_type(messages_chunk.message_type)
        if messages_chunk.message_type.is_backfill:
            indexnames = [self.current_indexname]
        else:
            indexnames = self._get_indexnames_for_alias(self._alias_for_keeping_live)
        _targetid_by_docid = {}
        done_counter = collections.Counter()
        bulk_stream = streaming_bulk(
            self.es8_client,
            self._elastic_actions_with_index(messages_chunk, indexnames, _targetid_by_docid),
            raise_on_error=False,
            max_retries=settings.ELASTICSEARCH['MAX_RETRIES'],
        )
        for (_ok, _response) in bulk_stream:
            (_op_type, _response_body) = next(iter(_response.items()))
            _status = _response_body.get('status')
            _docid = _response_body['_id']
            _is_done = _ok or (_op_type == 'delete' and _status == 404)
            _message_target_id = _targetid_by_docid[_docid]
            done_counter[_message_target_id] += 1
            if done_counter[_message_target_id] >= len(indexnames):
                yield messages.IndexMessageResponse(
                    is_done=_is_done,
                    index_message=messages.IndexMessage(messages_chunk.message_type, _message_target_id),
                    status_code=_response_body.get('status'),
                    error_text=(
                        None
                        if _ok
                        else str(_response_body)
                    )
                )

    # abstract method from IndexStrategy
    def pls_make_default_for_searching(self, specific_index: 'SpecificIndex'):
        self._set_indexnames_for_alias(
            self._alias_for_searching,
            {specific_index.indexname},
        )

    # abstract method from IndexStrategy
    def pls_get_default_for_searching(self) -> 'SpecificIndex':
        # a SpecificIndex for an alias will work fine for searching, but
        # will error if you try to invoke lifecycle hooks
        return self.for_specific_index(self._alias_for_searching)

    # override from IndexStrategy
    def pls_mark_backfill_complete(self):
        super().pls_mark_backfill_complete()
        # explicit refresh after bulk operation
        self.for_current_index().pls_refresh()

    @property
    def _alias_for_searching(self):
        return f'{self.indexname_prefix}search'

    @property
    def _alias_for_keeping_live(self):
        return f'{self.indexname_prefix}live'

    def _elastic_actions_with_index(self, messages_chunk, indexnames, targetid_by_docid):
        for _message_target_id, _elastic_action in self.build_elastic_actions(messages_chunk):
            targetid_by_docid[_elastic_action['_id']] = _message_target_id
            for _indexname in indexnames:
                yield {
                    **_elastic_action,
                    '_index': _indexname,
                }

    def _get_indexnames_for_alias(self, alias_name) -> set[str]:
        try:
            aliases = self.es8_client.indices.get_alias(name=alias_name)
            return set(aliases.keys())
        except elasticsearch8.exceptions.NotFoundError:
            return set()

    def _add_indexname_to_alias(self, alias_name, indexname):
        self.es8_client.indices.update_aliases(body={
            'actions': [
                {'add': {'index': indexname, 'alias': alias_name}},
            ],
        })

    def _remove_indexname_from_alias(self, alias_name, indexname):
        self.es8_client.indices.update_aliases(body={
            'actions': [
                {'remove': {'index': indexname, 'alias': alias_name}},
            ],
        })

    def _set_indexnames_for_alias(self, alias_name, indexnames):
        already_aliased = self._get_indexnames_for_alias(alias_name)
        want_aliased = set(indexnames)
        if already_aliased == want_aliased:
            logger.info(f'alias "{alias_name}" already correct ({want_aliased}), doing nothing')
        else:
            to_remove = tuple(already_aliased - want_aliased)
            to_add = tuple(want_aliased - already_aliased)
            logger.warning(f'alias "{alias_name}": removing indexes {to_remove} and adding indexes {to_add}')
            self.es8_client.indices.update_aliases(body={
                'actions': [
                    *(
                        {'remove': {'index': indexname, 'alias': alias_name}}
                        for indexname in to_remove
                    ),
                    *(
                        {'add': {'index': indexname, 'alias': alias_name}}
                        for indexname in to_add
                    ),
                ],
            })

    class SpecificIndex(IndexStrategy.SpecificIndex):

        # abstract method from IndexStrategy.SpecificIndex
        def pls_get_status(self) -> IndexStatus:
            if not self.pls_check_exists():
                return IndexStatus(
                    index_strategy_name=self.index_strategy.name,
                    specific_indexname=self.indexname,
                    is_kept_live=False,
                    is_default_for_searching=False,
                    doc_count=0,
                    creation_date='',
                )
            index_info = (
                self.index_strategy.es8_client.indices
                .get(index=self.indexname, features='aliases,settings')
                [self.indexname]
            )
            index_aliases = set(index_info['aliases'].keys())
            creation_date = _timestamp_to_readable_datetime(
                index_info['settings']['index']['creation_date']
            )
            doc_count = (
                self.index_strategy.es8_client
                .search(index=self.indexname, size=0, track_total_hits=True)
                ['hits']['total']['value']
            )
            return IndexStatus(
                index_strategy_name=self.index_strategy.name,
                specific_indexname=self.indexname,
                is_kept_live=(
                    self.index_strategy._alias_for_keeping_live
                    in index_aliases
                ),
                is_default_for_searching=(
                    self.index_strategy._alias_for_searching
                    in index_aliases
                ),
                creation_date=creation_date,
                doc_count=doc_count,
            )

        # abstract method from IndexStrategy.SpecificIndex
        def pls_check_exists(self):
            indexname = self.indexname
            logger.info(f'{self.__class__.__name__}: checking for index {indexname}')
            return bool(
                self.index_strategy.es8_client.indices
                .exists(index=indexname)
            )

        # abstract method from IndexStrategy.SpecificIndex
        def pls_create(self):
            assert self.is_current, (
                'cannot create a non-current version of an index!'
                ' maybe try `index_strategy.for_current_index()`?'
            )
            index_to_create = self.indexname
            logger.debug('Ensuring index %s', index_to_create)
            index_exists = (
                self.index_strategy.es8_client.indices
                .exists(index=index_to_create)
            )
            if not index_exists:
                logger.warning('Creating index %s', index_to_create)
                (
                    self.index_strategy.es8_client.indices
                    .create(
                        index=index_to_create,
                        settings=self.index_strategy.index_settings(),
                        mappings=self.index_strategy.index_mappings(),
                    )
                )
                self.pls_refresh()

        # abstract method from IndexStrategy.SpecificIndex
        def pls_refresh(self):
            (
                self.index_strategy.es8_client.indices
                .refresh(index=self.indexname)
            )
            logger.debug('%r: Waiting for yellow status', self)
            (
                self.index_strategy.es8_client.cluster
                .health(wait_for_status='yellow')
            )
            logger.info('%r: Refreshed', self)

        # abstract method from IndexStrategy.SpecificIndex
        def pls_delete(self):
            (
                self.index_strategy.es8_client.indices
                .delete(index=self.indexname, ignore=[400, 404])
            )
            logger.warning('%r: deleted', self)

        # abstract method from IndexStrategy.SpecificIndex
        def pls_start_keeping_live(self):
            self.index_strategy._add_indexname_to_alias(
                indexname=self.indexname,
                alias_name=self.index_strategy._alias_for_keeping_live,
            )
            logger.info('%r: now kept live', self)

        # abstract method from IndexStrategy.SpecificIndex
        def pls_stop_keeping_live(self):
            self.index_strategy._remove_indexname_from_alias(
                indexname=self.indexname,
                alias_name=self.index_strategy._alias_for_keeping_live,
            )
            logger.warning('%r: no longer kept live', self)
