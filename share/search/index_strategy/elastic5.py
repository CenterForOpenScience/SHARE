import abc
import datetime
import logging
import typing

from django.conf import settings
from elasticsearch5 import Elasticsearch, helpers as elastic5_helpers

from share.search import messages
from share.search.index_status import IndexStatus
from share.search.index_strategy._base import IndexStrategy


logger = logging.getLogger(__name__)


class Elastic5IndexStrategy(IndexStrategy):
    SUPPORTS_BACKFILL = False

    # use a simple constant instead of the fancy versioning logic in base IndexStrategy
    # -- intent is to put new indexes in elastic8+ and drop elastic5 soon
    INDEXNAME = None

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
    def indexname_prefix(self):
        return self.INDEXNAME

    @property
    # override IndexStrategy
    def _current_indexname(self):
        return self.INDEXNAME

    # abstract method from IndexStrategy
    def current_setup(self):
        return {
            'indexname': self.INDEXNAME,
            'settings': self.index_settings(),
            'mappings': self.index_mappings(),
        }

    # abstract method from IndexStrategy
    def get_indexname_for_searching(self):
        return self.INDEXNAME

    # abstract method from IndexStrategy
    def get_indexnames_for_keeping_live(self):
        return {self.INDEXNAME}

    # abstract method from IndexStrategy
    def pls_make_default_for_searching(self):
        logger.info(
            'Elastic5IndexStrategy.pls_make_default_for_searching doing nothing with '
            'the expectation we will stop using elasticsearch5 soon'
        )

    # abstract method from IndexStrategy
    def pls_create(self):
        # check index exists (if not, create)
        indexname = self.indexname
        logger.debug('Ensuring index %s', indexname)
        if not self.es5_client.indices.exists(index=indexname):
            (
                self.es5_client
                .indices
                .create(
                    indexname,
                    body={
                        'settings': self.index_settings(),
                        'mappings': self.index_mappings(),
                    },
                )
            )
        self.es5_client.indices.refresh(index=indexname)
        logger.debug('Waiting for yellow status')
        self.es5_client.cluster.health(wait_for_status='yellow')
        logger.info('Finished setting up Elasticsearch index %s', indexname)

    # abstract method from IndexStrategy
    def pls_delete(self):
        indexname = self.indexname
        logger.warning(f'{self.__class__.__name__}: deleting index {indexname}')
        (
            self.es5_client
            .indices
            .delete(index=indexname, ignore=[400, 404])
        )

    # abstract method from IndexStrategy
    def pls_check_exists(self):
        indexname = self.indexname
        logger.info(f'{self.__class__.__name__}: checking for index {indexname}')
        return (
            self.es5_client
            .indices
            .exists(index=indexname)
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
            is_handled = ok or (op_type == 'delete' and response_body.get('result') == 'not_found')
            error_label = None if is_handled else response_body
            yield messages.IndexMessageResponse(
                is_handled=is_handled,
                index_message=messages.IndexMessage(messages_chunk.message_type, message_target_id),
                error_label=error_label,
            )

    # abstract method from IndexStrategy
    def specific_index_statuses(self) -> typing.Iterable[IndexStatus]:
        stats = self.es5_client.indices.stats(
            index=self.INDEXNAME,
            metric='docs',
        )
        existing_indexes = self.es5_client.indices.get_settings(
            index=self.INDEXNAME,
            name='index.creation_date',
        )
        try:
            index_settings = existing_indexes[self.INDEXNAME]
            index_stats = stats['indices'][self.INDEXNAME]
        except KeyError:
            yield IndexStatus(
                specific_indexname=self.INDEXNAME,
                is_current=True,
                is_kept_live=False,
                is_default_for_searching=True,
                creation_date=None,
                doc_count=0,
                health='nonexistent',
            )
        else:
            timestamp_milliseconds = int(index_settings['settings']['index']['creation_date'])
            timestamp_seconds = timestamp_milliseconds / 1000
            creation_date = (
                datetime.datetime
                .fromtimestamp(timestamp_seconds, tz=datetime.timezone.utc)
                .isoformat(timespec='minutes')
            )
            yield IndexStatus(
                specific_indexname=self.INDEXNAME,
                is_current=True,
                is_kept_live=True,
                is_default_for_searching=True,
                creation_date=creation_date,
                doc_count=index_stats['primaries']['docs']['count'],
                health='ok?',
            )

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
