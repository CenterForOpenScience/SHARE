import abc
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
            # auth:
            http_auth=self.cluster_auth,
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
    def pls_open_for_searching(self, *, specific_index_name=None):
        index_to_open = specific_index_name or self.current_index_name
        indexes_open = self._indexes_open_for_searching()
        if indexes_open != {index_to_open}:
            indexes_open.discard(index_to_open)
            logger.warning(f'removing aliases to {indexes_open} and adding alias to {self.current_index_name}')
            delete_actions = [
                {'remove': {'index': index_name, 'alias': self.alias_for_searching}}
                for index_name in indexes_open
            ]
            add_action = {'add': {'index': self.current_index_name, 'alias': self.alias_for_searching}}
            self.es8_client.indices.update_aliases(body={
                'actions': [
                    *delete_actions,
                    add_action
                ],
            })

    def _indexes_open_for_searching(self):
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
        indexes_open = self._indexes_open_for_searching()
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
        logger.debug('Ensuring index %s', self.current_index_name)
        index_exists = (
            self.es8_client
            .indices
            .exists(index=self.current_index_name)
        )
        if not index_exists:
            logger.warning('Creating index %s', self.current_index_name)
            (
                self.es8_client
                .indices
                .create(
                    index=self.current_index_name,
                    settings=self.index_settings(),
                    mappings=self.index_mappings(),
                )
            )
        self.es8_client.indices.refresh(index=self.current_index_name)
        logger.debug('Waiting for yellow status')
        self.es8_client.cluster.health(wait_for_status='yellow')
        logger.info('Finished setting up Elasticsearch index %s', self.current_index_name)

    # implements IndexStrategy.pls_delete
    def pls_delete(self, *, specific_index_name=None):
        index_name = specific_index_name or self.current_index_name
        logger.warning(f'{self.__class__.__name__}: deleting index {index_name}')
        (
            self.es8_client
            .indices
            .delete(index=index_name, ignore=[400, 404])
        )

    # implements IndexStrategy.pls_check_exists
    def pls_check_exists(self, *, specific_index_name=None):
        index_name = specific_index_name or self.current_index_name
        logger.info(f'{self.__class__.__name__}: checking for index {index_name}')
        return (
            self.es8_client
            .indices
            .exists(index=index_name)
        )

    def pls_handle_messages_chunk(self, messages_chunk):
        bulk_stream = streaming_bulk(
            self.es8_client,
            self.build_elastic_actions(messages_chunk),
            raise_on_error=False,
        )
        for (ok, response) in bulk_stream:
            op_type, response_body = next(iter(response.items()))
            message_target_id = self.get_message_target_id(response_body['_id'])
            yield messages.IndexMessageResponse(
                is_handled=ok,
                index_message=messages.IndexMessage(messages_chunk.message_type, message_target_id),
                error_label=response_body.get('_errors'),
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
