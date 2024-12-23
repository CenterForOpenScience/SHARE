from __future__ import annotations
import abc
import collections
import dataclasses
from http import HTTPStatus
import logging
import typing

from django.conf import settings
import elasticsearch8
from elasticsearch8.helpers import streaming_bulk

from share.search.index_strategy._base import IndexStrategy
from share.search.index_status import IndexStatus
from share.search import messages
from share.search.index_strategy._util import timestamp_to_readable_datetime
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
            settings.ELASTICSEARCH8_URL,
            # security:
            ca_certs=settings.ELASTICSEARCH8_CERT_PATH,
            basic_auth=(
                (settings.ELASTICSEARCH8_USERNAME, settings.ELASTICSEARCH8_SECRET)
                if settings.ELASTICSEARCH8_SECRET is not None
                else None
            ),
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
    def build_elastic_actions(
        self,
        messages_chunk: messages.MessagesChunk,
    ) -> typing.Iterable[tuple[int, dict | typing.Iterable[dict]]]:
        # yield (message_target_id, [elastic_action, ...]) pairs
        raise NotImplementedError

    def before_chunk(
        self,
        messages_chunk: messages.MessagesChunk,
        indexnames: typing.Iterable[str],
    ) -> None:
        ...  # implement when needed

    def after_chunk(
        self,
        messages_chunk: messages.MessagesChunk,
        indexnames: typing.Iterable[str],
    ) -> None:
        ...  # implement when needed

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

    def build_update_action(self, doc_id, doc_source):
        return {
            '_op_type': 'update',
            '_id': str(doc_id),
            'doc': doc_source,
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
            _indexnames = {self.current_indexname}
        else:
            _indexnames = self._get_indexnames_for_alias(self._alias_for_keeping_live)
        self.before_chunk(messages_chunk, _indexnames)
        _action_tracker = _ActionTracker()
        _bulk_stream = streaming_bulk(
            self.es8_client,
            self._elastic_actions_with_index(messages_chunk, _indexnames, _action_tracker),
            raise_on_error=False,
            max_retries=settings.ELASTICSEARCH['MAX_RETRIES'],
        )
        for (_ok, _response) in _bulk_stream:
            (_op_type, _response_body) = next(iter(_response.items()))
            _status = _response_body.get('status')
            _docid = _response_body['_id']
            _indexname = _response_body['_index']
            _is_done = _ok or (_op_type == 'delete' and _status == 404)
            if _is_done:
                _finished_message_id = _action_tracker.action_done(_indexname, _docid)
                if _finished_message_id is not None:
                    yield messages.IndexMessageResponse(
                        is_done=True,
                        index_message=messages.IndexMessage(messages_chunk.message_type, _finished_message_id),
                        status_code=HTTPStatus.OK.value,
                        error_text=None,
                    )
                    _action_tracker.forget_message(_finished_message_id)
            else:
                _action_tracker.action_errored(_indexname, _docid)
                yield messages.IndexMessageResponse(
                    is_done=False,
                    index_message=messages.IndexMessage(
                        messages_chunk.message_type,
                        _action_tracker.get_message_id(_docid),
                    ),
                    status_code=_status,
                    error_text=str(_response_body),
                )
        for _message_id in _action_tracker.remaining_done_messages():
            yield messages.IndexMessageResponse(
                is_done=True,
                index_message=messages.IndexMessage(messages_chunk.message_type, _message_id),
                status_code=HTTPStatus.OK.value,
                error_text=None,
            )
        self.after_chunk(messages_chunk, _indexnames)

    # abstract method from IndexStrategy
    def pls_make_default_for_searching(self, specific_index: IndexStrategy.SpecificIndex):
        self._set_indexnames_for_alias(
            self._alias_for_searching,
            {specific_index.indexname},
        )

    # abstract method from IndexStrategy
    def pls_get_default_for_searching(self) -> IndexStrategy.SpecificIndex:
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

    def _elastic_actions_with_index(self, messages_chunk, indexnames, action_tracker: _ActionTracker):
        if not indexnames:
            raise ValueError('cannot index to no indexes')
        for _message_target_id, _elastic_actions in self.build_elastic_actions(messages_chunk):
            if isinstance(_elastic_actions, dict):  # allow a single action
                _elastic_actions = [_elastic_actions]
            for _elastic_action in _elastic_actions:
                _docid = _elastic_action['_id']
                for _indexname in indexnames:
                    action_tracker.add_action(_message_target_id, _indexname, _docid)
                    yield {
                        **_elastic_action,
                        '_index': _indexname,
                    }
            action_tracker.done_scheduling(_message_target_id)

    def _get_indexnames_for_alias(self, alias_name) -> set[str]:
        try:
            aliases = self.es8_client.indices.get_alias(name=alias_name)
            return set(aliases.keys())
        except elasticsearch8.exceptions.NotFoundError:
            return set()

    def _add_indexname_to_alias(self, alias_name, indexname):
        self.es8_client.indices.update_aliases(actions=[
            {'add': {'index': indexname, 'alias': alias_name}},
        ])

    def _remove_indexname_from_alias(self, alias_name, indexname):
        self.es8_client.indices.update_aliases(actions=[
            {'remove': {'index': indexname, 'alias': alias_name}},
        ])

    def _set_indexnames_for_alias(self, alias_name, indexnames):
        already_aliased = self._get_indexnames_for_alias(alias_name)
        want_aliased = set(indexnames)
        if already_aliased == want_aliased:
            logger.info(f'alias "{alias_name}" already correct ({want_aliased}), doing nothing')
        else:
            to_remove = tuple(already_aliased - want_aliased)
            to_add = tuple(want_aliased - already_aliased)
            logger.warning(f'alias "{alias_name}": removing indexes {to_remove} and adding indexes {to_add}')
            self.es8_client.indices.update_aliases(actions=[
                *(
                    {'remove': {'index': indexname, 'alias': alias_name}}
                    for indexname in to_remove
                ),
                *(
                    {'add': {'index': indexname, 'alias': alias_name}}
                    for indexname in to_add
                ),
            ])

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
            creation_date = timestamp_to_readable_datetime(
                index_info['settings']['index']['creation_date']
            )
            doc_count = (
                self.index_strategy.es8_client.indices
                .stats(index=self.indexname, metric='docs')
                ['indices'][self.indexname]['primaries']['docs']['count']
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

        def pls_get_mappings(self):
            return self.index_strategy.es8_client.indices.get_mapping(index=self.indexname).body


@dataclasses.dataclass
class _ActionTracker:
    messageid_by_docid: dict[str, int] = dataclasses.field(default_factory=dict)
    actions_by_messageid: dict[int, set[tuple[str, str]]] = dataclasses.field(
        default_factory=lambda: collections.defaultdict(set),
    )
    errored_messageids: set[int] = dataclasses.field(default_factory=set)
    fully_scheduled_messageids: set[int] = dataclasses.field(default_factory=set)

    def add_action(self, message_id: int, index_name: str, doc_id: str):
        self.messageid_by_docid[doc_id] = message_id
        self.actions_by_messageid[message_id].add((index_name, doc_id))

    def action_done(self, index_name: str, doc_id: str) -> int | None:
        _messageid = self.get_message_id(doc_id)
        _remaining_message_actions = self.actions_by_messageid[_messageid]
        _remaining_message_actions.discard((index_name, doc_id))
        # return the message id only if this was the last action for that message
        return (
            None
            if _remaining_message_actions or (_messageid not in self.fully_scheduled_messageids)
            else _messageid
        )

    def action_errored(self, index_name: str, doc_id: str):
        _messageid = self.messageid_by_docid[doc_id]
        self.errored_messageids.add(_messageid)

    def done_scheduling(self, message_id: int):
        self.fully_scheduled_messageids.add(message_id)

    def forget_message(self, message_id: int):
        del self.actions_by_messageid[message_id]

    def get_message_id(self, doc_id: str):
        return self.messageid_by_docid[doc_id]

    def remaining_done_messages(self):
        for _messageid, _actions in self.actions_by_messageid.items():
            if _messageid not in self.errored_messageids:
                assert not _actions
                yield _messageid
