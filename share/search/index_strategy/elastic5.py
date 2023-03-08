import abc
import datetime
import logging

from django.conf import settings
from elasticsearch5 import Elasticsearch, helpers as elastic5_helpers

from share.search import messages
from share.search.index_strategy._base import IndexStrategy


logger = logging.getLogger(__name__)


class Elastic5IndexStrategy(IndexStrategy):
    # use a simple constant instead of the fancy versioning logic in base IndexStrategy
    # -- intent is to put new indexes in elastic8+ and drop elastic5 soon
    INDEX_NAME = None

    # perpetuated optimizations from times long past
    MAX_CHUNK_BYTES = 10 * 1024 ** 2  # 10 megs

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        should_sniff = settings.ELASTICSEARCH['SNIFF']
        self.es5_client = Elasticsearch(
            self.cluster_url,
            retry_on_timeout=True,
            timeout=settings.ELASTICSEARCH['TIMEOUT'],
            # sniff before doing anything
            sniff_on_start=should_sniff,
            # refresh nodes after a node fails to respond
            sniff_on_connection_fail=should_sniff,
            # and also every 60 seconds
            sniffer_timeout=60 if should_sniff else None,
        )

    @property
    # override IndexStrategy
    def current_index_prefix(self):
        return self.INDEX_NAME

    @property
    # override IndexStrategy
    def current_index_name(self):
        return self.INDEX_NAME

    @property
    # override IndexStrategy
    def alias_for_searching(self):
        return self.INDEX_NAME

    # abstract method from IndexStrategy
    def pls_get_indexnames_open_for_searching(self):
        return {self.INDEX_NAME}

    # abstract method from IndexStrategy
    def current_setup(self):
        return {
            'settings': self.index_settings(),
            'mappings': self.index_mappings(),
        }

    # abstract method from IndexStrategy
    def pls_open_for_searching(self):
        logger.info(
            'Elastic5IndexStrategy.pls_open_for_searching doing nothing with '
            'the expectation we will stop using elasticsearch5 soon'
        )

    # abstract method from IndexStrategy
    def pls_create(self):
        # check index exists (if not, create)
        index_name = self.get_specific_indexname()
        logger.debug('Ensuring index %s', index_name)
        if not self.es5_client.indices.exists(index=index_name):
            (
                self.es5_client
                .indices
                .create(
                    index_name,
                    body={
                        'settings': self.index_settings(),
                        'mappings': self.index_mappings(),
                    },
                )
            )
        self.es5_client.indices.refresh(index=index_name)
        logger.debug('Waiting for yellow status')
        self.es5_client.cluster.health(wait_for_status='yellow')
        logger.info('Finished setting up Elasticsearch index %s', index_name)

    # abstract method from IndexStrategy
    def pls_delete(self):
        index_name = self.get_specific_indexname()
        logger.warning(f'{self.__class__.__name__}: deleting index {index_name}')
        (
            self.es5_client
            .indices
            .delete(index=index_name, ignore=[400, 404])
        )

    # abstract method from IndexStrategy
    def pls_check_exists(self):
        index_name = self.get_specific_indexname()
        logger.info(f'{self.__class__.__name__}: checking for index {index_name}')
        return (
            self.es5_client
            .indices
            .exists(index=index_name)
        )

    # abstract method from IndexStrategy
    def pls_handle_messages_chunk(self, messages_chunk):
        bulk_stream = elastic5_helpers.streaming_bulk(
            self.es5_client,
            self.build_elastic_actions(messages_chunk),
            max_chunk_bytes=self.MAX_CHUNK_BYTES,
            raise_on_error=False,
        )
        for (ok, response) in bulk_stream:
            op_type, response_body = next(iter(response.items()))
            message_target_id = self.get_message_target_id(response_body['_id'])
            yield messages.IndexMessageResponse(
                is_handled=ok,
                index_message=messages.IndexMessage(messages_chunk.message_type, message_target_id),
                error_label=response_body,
            )

    # abstract method from IndexStrategy
    def specific_index_statuses(self):
        stats = self.es5_client.indices.stats(
            index=self.current_index_wildcard,
            metric='docs',
        )
        existing_indexes = self.es5_client.indices.get_settings(
            index=self.current_index_wildcard,
            name='index.creation_date',
        )
        creation_dates = {}
        for index_name, index_settings in existing_indexes.items():
            timestamp_milliseconds = int(index_settings['settings']['index']['creation_date'])
            timestamp_seconds = timestamp_milliseconds / 1000
            creation_dates[index_name] = (
                datetime.datetime
                .fromtimestamp(timestamp_seconds, tz=datetime.timezone.utc)
                .isoformat(timespec='minutes')
            )
        index_statuses = {
            index_name: {
                'is_current': index_name == self.current_index_name,
                'is_open_for_searching': True,
                'doc_count': index_stats['primaries']['docs']['count'],
                'creation_date': creation_dates.get(index_name),
            }
            for index_name, index_stats in stats['indices'].items()
        }
        if self.current_index_name not in index_statuses:
            index_statuses[self.current_index_name] = {
                'is_current': True,
                'is_open_for_searching': False,
                'doc_count': 0,
                'health': 'nonexistent',
                'creation_date': None,
            }
        return index_statuses

    @abc.abstractmethod
    def index_settings(self):
        raise NotImplementedError

    @abc.abstractmethod
    def index_mappings(self):
        raise NotImplementedError

    @abc.abstractmethod
    def get_message_target_id(self, doc_id):
        raise NotImplementedError

    @abc.abstractmethod
    def build_elastic_actions(self, messages_chunk):
        raise NotImplementedError
