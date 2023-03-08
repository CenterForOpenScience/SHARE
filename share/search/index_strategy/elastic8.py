import abc
import collections
import datetime
import logging

from django.conf import settings
import elasticsearch8
from elasticsearch8.helpers import streaming_bulk

from share.search.index_strategy._base import IndexStrategy
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

    # implements IndexStrategy.current_setup
    def current_setup(self):
        return {
            'settings': self.index_settings(),
            'mappings': self.index_mappings(),
        }

    # implements IndexStrategy.pls_open_for_searching
    def pls_open_for_searching(self):
        index_to_open = self.get_specific_indexname()
        indexes_already_open = self.pls_get_indexnames_open_for_searching()
        if indexes_already_open != {index_to_open}:
            indexes_already_open.discard(index_to_open)
            logger.warning(f'removing aliases to {indexes_already_open} and adding alias to {index_to_open}')
            delete_actions = [
                {'remove': {'index': index_name, 'alias': self.alias_for_searching}}
                for index_name in indexes_already_open
            ]
            add_action = {'add': {'index': index_to_open, 'alias': self.alias_for_searching}}
            self.es8_client.indices.update_aliases(body={
                'actions': [
                    *delete_actions,
                    add_action
                ],
            })

    # abstract method from IndexStrategy
    def pls_get_indexnames_open_for_searching(self):
        try:
            aliases = self.es8_client.indices.get_alias(name=self.alias_for_searching)
            return set(aliases.keys())
        except elasticsearch8.exceptions.NotFoundError:
            return set()

    def specific_index_statuses(self):
        stats = self.es8_client.indices.stats(
            index=self.current_index_wildcard,
            metric='docs',
        )
        creation_dates = self._get_index_creation_dates()
        indexes_open = self.pls_get_indexnames_open_for_searching()
        index_statuses = {
            index_name: {
                'is_current': index_name == self.current_index_name,
                'is_open_for_searching': index_name in indexes_open,
                'doc_count': index_stats['primaries']['docs']['count'],
                'health': index_stats['health'],
                'creation_date': creation_dates.get(index_name),
            }
            for index_name, index_stats in stats['indices'].items()
        }
        if self.current_index_name not in index_statuses:
            index_statuses[self.current_index_name] = {
                'is_current': True,
                'is_open_for_searching': self.current_index_name in indexes_open,
                'doc_count': 0,
                'health': 'nonexistent',
                'creation_date': None,
            }
        return index_statuses

    # implements IndexStrategy.pls_create
    def pls_create(self):
        index_to_create = self.get_specific_indexname()
        assert index_to_create == self.current_index_name, (
            'cannot create a non-current version of an index! '
            'to proceed, use an index strategy without `specific_index_name`'
        )
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

    # implements IndexStrategy.pls_delete
    def pls_delete(self):
        index_to_delete = self.get_specific_indexname()
        logger.warning(f'{self.__class__.__name__}: deleting index {index_to_delete}')
        (
            self.es8_client
            .indices
            .delete(index=index_to_delete, ignore=[400, 404])
        )

    # implements IndexStrategy.pls_check_exists
    def pls_check_exists(self):
        index_name = self.get_specific_indexname()
        logger.info(f'{self.__class__.__name__}: checking for index {index_name}')
        return (
            self.es8_client
            .indices
            .exists(index=index_name)
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
        indexnames = self.get_indexnames_for_updating(messages_chunk.message_type)
        done_counter = collections.Counter()
        bulk_stream = streaming_bulk(
            self.es8_client,
            self._elastic_actions_with_index(messages_chunk, indexnames),
            raise_on_error=False,
        )
        for (ok, response) in bulk_stream:
            op_type, response_body = next(iter(response.items()))
            message_target_id = self.get_message_target_id(response_body['_id'])
            done_counter[message_target_id] += 1
            if done_counter[message_target_id] >= len(indexnames):
                yield messages.IndexMessageResponse(
                    is_handled=ok,
                    index_message=messages.IndexMessage(messages_chunk.message_type, message_target_id),
                    error_label=response_body,
                )

    def _get_index_creation_dates(self):
        existing_index_settings = self.es8_client.indices.get_settings(
            index=self.current_index_wildcard,
            name='index.creation_date',
        )
        creation_dates = {}
        for index_name, index_settings in existing_index_settings.items():
            timestamp_milliseconds = int(index_settings['settings']['index']['creation_date'])
            timestamp_seconds = timestamp_milliseconds / 1000
            creation_dates[index_name] = (
                datetime.datetime
                .fromtimestamp(timestamp_seconds, tz=datetime.timezone.utc)
                .isoformat(timespec='minutes')
            )
        return creation_dates
