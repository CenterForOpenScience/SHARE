import abc
import collections
import datetime
import logging
import typing

from django.conf import settings
import elasticsearch8
from elasticsearch8.helpers import streaming_bulk

from share.search.index_strategy._base import IndexStrategy
from share.search.index_status import IndexStatus
from share.search import messages


logger = logging.getLogger(__name__)


class Elastic8IndexStrategy(IndexStrategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        should_sniff = settings.ELASTICSEARCH['SNIFF']
        timeout = settings.ELASTICSEARCH['TIMEOUT']
        self.es8_client = elasticsearch8.Elasticsearch(
            self.cluster_url,
            # security:
            ca_certs=self.cluster_settings.get('CERT_PATH'),
            http_auth=self.cluster_settings.get('AUTH'),
            # retry:
            retry_on_timeout=True,
            timeout=timeout,
            # sniffing:
            sniff_on_start=should_sniff,
            sniff_before_requests=should_sniff,
            sniff_on_node_failure=should_sniff,
            sniff_timeout=timeout,
            min_delay_between_sniffing=timeout,
        )

    @abc.abstractmethod
    def index_settings(self):
        raise NotImplementedError  # for subclasses to implement

    @abc.abstractmethod
    def index_mappings(self):
        raise NotImplementedError  # for subclasses to implement

    @abc.abstractmethod
    def build_elastic_actions(self, messages_chunk: messages.MessagesChunk):
        raise NotImplementedError  # for subclasses to implement

    def get_doc_id(self, message_target_id):
        return message_target_id  # here so subclasses can override if needed

    def get_message_target_id(self, doc_id):
        return doc_id  # here so subclasses can override if needed

    @property
    def alias_for_searching(self):
        return f'{self.indexname_prefix}search'

    @property
    def alias_for_keeping_live(self):
        return f'{self.indexname_prefix}live'

    # abstract method from IndexStrategy
    def current_setup(self):
        return {
            'settings': self.index_settings(),
            'mappings': self.index_mappings(),
        }

    # abstract method from IndexStrategy
    def pls_keep_live(self):
        self.es8_client.indices.update_aliases(body={
            'actions': [
                {'add': {'index': self.indexname, 'alias': self.alias_for_keeping_live}}
            ],
        })

    # abstract method from IndexStrategy
    def pls_stop_keeping_live(self):
        self.es8_client.indices.update_aliases(body={
            'actions': [
                {'remove': {'index': self.indexname, 'alias': self.alias_for_keeping_live}}
            ],
        })

    # abstract method from IndexStrategy
    def pls_make_default_for_searching(self):
        self._set_indexnames_for_alias(self.alias_for_searching, {self.indexname})

    # abstract method from IndexStrategy
    def get_indexname_for_searching(self):
        indexnames = self._get_indexnames_for_alias(self.alias_for_searching)
        assert len(indexnames) == 1
        return indexnames.pop()

    # abstract method from IndexStrategy
    def get_indexnames_for_keeping_live(self):
        return self._get_indexnames_for_alias(self.alias_for_keeping_live)

    # abstract method from IndexStrategy
    def specific_index_statuses(self) -> typing.Iterable[IndexStatus]:
        stats = self.es8_client.indices.stats(
            index=self.indexname_wildcard,
            metric='docs',
        )
        creation_dates = self._get_index_creation_dates()
        search_indexname = self.get_indexname_for_searching()
        live_indexnames = self.get_indexnames_for_keeping_live()
        current_indexname = self._current_indexname
        got_current = False
        for indexname, index_stats in stats['indices'].items():
            if indexname == current_indexname:
                got_current = True
            yield IndexStatus(
                specific_indexname=indexname,
                is_current=(indexname == current_indexname),
                is_kept_live=(indexname in live_indexnames),
                is_default_for_searching=(indexname == search_indexname),
                creation_date=creation_dates.get(indexname),
                doc_count=index_stats['primaries']['docs']['count'],
                health=index_stats['health'],
            )
        if not got_current:
            yield IndexStatus(
                specific_indexname=current_indexname,
                is_current=True,
                is_kept_live=(current_indexname in live_indexnames),
                is_default_for_searching=(current_indexname == search_indexname),
                doc_count=0,
                health='nonexistent',
                creation_date='',
            )

    # abstract method from IndexStrategy
    def pls_create(self):
        assert self.is_current, (
            'cannot create a non-current version of an index! '
            'to proceed, use an index strategy without `specific_indexname`'
        )
        index_to_create = self.indexname
        logger.debug('Ensuring index %s', index_to_create)
        index_exists = (
            self.es8_client
            .indices
            .exists(index=index_to_create)
        )
        if not index_exists:
            logger.warning('Creating index %s', index_to_create)
            (
                self.es8_client
                .indices
                .create(
                    index=index_to_create,
                    settings=self.index_settings(),
                    mappings=self.index_mappings(),
                )
            )
        self.es8_client.indices.refresh(index=index_to_create)
        logger.debug('Waiting for yellow status')
        self.es8_client.cluster.health(wait_for_status='yellow')
        logger.info('Finished setting up Elasticsearch index %s', index_to_create)

    # abstract method from IndexStrategy
    def pls_delete(self):
        index_to_delete = self.indexname
        logger.warning(f'{self.__class__.__name__}: deleting index {index_to_delete}')
        (
            self.es8_client
            .indices
            .delete(index=index_to_delete, ignore=[400, 404])
        )

    # abstract method from IndexStrategy
    def pls_check_exists(self):
        indexname = self.indexname
        logger.info(f'{self.__class__.__name__}: checking for index {indexname}')
        return (
            self.es8_client
            .indices
            .exists(index=indexname)
        )

    def _elastic_actions_with_index(self, messages_chunk, indexnames):
        for elastic_action in self.build_elastic_actions(messages_chunk):
            for indexname in indexnames:
                yield {
                    '_index': indexname,
                    **elastic_action,
                }

    def pls_handle_messages_chunk(self, messages_chunk):
        self.assert_message_type(messages_chunk.message_type)
        indexnames = self.get_indexnames_for_keeping_live(messages_chunk.message_type)
        done_counter = collections.Counter()
        bulk_stream = streaming_bulk(
            self.es8_client,
            self._elastic_actions_with_index(messages_chunk, indexnames),
            raise_on_error=False,
        )
        for (ok, response) in bulk_stream:
            op_type, response_body = next(iter(response.items()))
            is_handled = ok or (op_type == 'delete' and response_body.get('result') == 'not_found')
            message_target_id = self.get_message_target_id(response_body['_id'])
            done_counter[message_target_id] += 1
            if done_counter[message_target_id] >= len(indexnames):
                yield messages.IndexMessageResponse(
                    is_handled=is_handled,
                    index_message=messages.IndexMessage(messages_chunk.message_type, message_target_id),
                    error_label=response_body,
                )

    def _get_index_creation_dates(self):
        existing_index_settings = self.es8_client.indices.get_settings(
            index=self.indexname_wildcard,
            name='index.creation_date',
        )
        creation_dates = {}
        for indexname, index_settings in existing_index_settings.items():
            timestamp_milliseconds = int(index_settings['settings']['index']['creation_date'])
            timestamp_seconds = timestamp_milliseconds / 1000
            creation_dates[indexname] = (
                datetime.datetime
                .fromtimestamp(timestamp_seconds, tz=datetime.timezone.utc)
                .isoformat(timespec='minutes')
            )
        return creation_dates

    def _get_indexnames_for_alias(self, alias_name) -> set[str]:
        try:
            aliases = self.es8_client.indices.get_alias(name=alias_name)
            return set(aliases.keys())
        except elasticsearch8.exceptions.NotFoundError:
            return set()

    def _set_indexnames_for_alias(self, alias_name, indexnames):
        already_aliased = self._get_indexnames_for_alias(alias_name)
        want_aliased = set(indexnames)
        if already_aliased == want_aliased:
            logger.info(f'alias "{alias_name}" already correct ({want_aliased}), doing nothing')
        else:
            to_remove = already_aliased - want_aliased
            to_add = want_aliased - already_aliased
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
