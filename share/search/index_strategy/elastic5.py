import abc
import datetime
import logging

from django.conf import settings
from elasticsearch5 import Elasticsearch, helpers as elastic5_helpers

from share.search.index_strategy._base import IndexStrategy


logger = logging.getLogger(__name__)


class Elastic5IndexStrategy(IndexStrategy):
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

    @abc.abstractmethod
    def index_settings(self):
        raise NotImplementedError

    @abc.abstractmethod
    def index_mappings(self):
        raise NotImplementedError

    @abc.abstractmethod
    def build_elastic_actions(self, messages_chunk):
        raise NotImplementedError

    def current_setup(self):
        return {
            'settings': self.index_settings(),
            'mappings': self.index_mappings(),
        }

    def pls_make_prime(self):
        logger.info(
            'Elastic5IndexStrategy.pls_make_prime doing nothing with '
            'the expectation we will stop using elasticsearch5 soon'
        )

    def pls_create(self):
        logger.debug('Ensuring index %s', self.name)
        # check index exists (if not, create)
        if not self.es5_client.indices.exists(index=self.name):
            (
                self.es5_client
                .indices
                .create(
                    index=self.name,
                    settings=self.index_settings(),
                    mappings=self.index_mappings(),
                )
            )
        self.es5_client.indices.refresh(index=self.name)
        logger.debug('Waiting for yellow status')
        self.es5_client.cluster.health(wait_for_status='yellow')
        logger.info('Finished setting up Elasticsearch index %s', self.name)

    def pls_delete(self):
        logger.warning(f'{self.__class__.__name__}: deleting index {self.index_name}')
        (
            self.es5_client
            .indices
            .delete(index=self.name, ignore=[400, 404])
        )

    def pls_handle_messages_chunk(self, messages_chunk):
        (success_count, errors) = elastic5_helpers.bulk(
            self.es5_client,
            self.build_elastic_actions(messages_chunk),
            raise_on_error=False,
        )
        print((success_count, errors))
        import pdb; pdb.set_trace()
        for error in errors:
            # yield error response
            pass

    def specific_index_statuses(self):
        self.es5_client.indices.refresh()
        stats = self.es5_client.indices.stats(
            index=self.current_index_wildcard,
            metric='docs',
        )
        creation_dates = self._get_index_creation_dates()
        index_statuses = {
            index_name: {
                'is_current': index_name == self.current_index_name,
                'is_prime': True,
                'doc_count': index_stats['primaries']['docs']['count'],
                'creation_date': creation_dates.get(index_name),
            }
            for index_name, index_stats in stats['indices'].items()
        }
        if self.current_index_name not in index_statuses:
            index_statuses[self.current_index_name] = {
                'is_current': True,
                'is_prime': True,
                'doc_count': 0,
                'health': 'nonexistent',
                'creation_date': None,
            }
        return index_statuses

    def _get_index_creation_dates(self):
        existing_index_settings = self.es5_client.indices.get_settings(
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
