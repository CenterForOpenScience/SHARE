from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
import logging
import queue
import threading
import time

from django.conf import settings

from elasticsearch import Elasticsearch
from elasticsearch import helpers

from raven.contrib.django.raven_compat.models import client

from share import util
from share.search.indexing import ElasticsearchActionGenerator


logger = logging.getLogger(__name__)


class FutureManager:

    def __init__(self):
        self._not_done = []

    def add(self, future):
        self._not_done.append(future)

    def cancel_all(self):
        self.report()
        for fut in self._not_done:
            fut.cancel()

    def report(self):
        if not self._not_done:
            return

        # NOTE: This will block until at least one task terminates
        # If ES starts lagging behind, at least this will slow the indexer down
        done, self._not_done = futures.wait(self._not_done, return_when=futures.FIRST_COMPLETED)
        self._not_done = list(self._not_done)

        errored, completed = [], []
        for fut in done:
            if not fut.exception():
                completed.append(fut)
            else:
                errored.append(fut)
                logger.exception('Indexing attempt failed', exc_info=fut.exception())

        logger.info('Completed Tasks: %d, Errored Tasks: %d, Pending Tasks: %d', len(completed), len(errored), len(self._not_done))


class SearchIndexerDaemon(threading.Thread):

    MAX_CHUNK_BYTES = 10 * 1024 ** 2  # 10 megs

    def __init__(self, celery_app, queue_name, indexes, url=None):
        super().__init__(daemon=True, name=queue_name)  # It's fine to kill this thread whenever if need be

        self.celery_app = celery_app

        self.rabbit_connection = None
        self.rabbit_queue = None
        self.rabbit_queue_name = queue_name

        self.es_client = None
        self.es_indexes = indexes
        self.es_url = url or settings.ELASTICSEARCH_URL

        self.connection_errors = ()
        self.keep_running = threading.Event()

    def initialize(self):
        logger.info('Initializing %r', self)

        logger.debug('Connecting to Elasticsearch cluster at "%s"', self.es_url)
        try:
            if settings.ELASTICSEARCH['SNIFF']:
                logger.info('Elasticsearch sniffing is enabled')

            self.es_client = Elasticsearch(
                self.es_url,
                retry_on_timeout=True,
                timeout=settings.ELASTICSEARCH_TIMEOUT,
                # sniff before doing anything
                sniff_on_start=settings.ELASTICSEARCH['SNIFF'],
                # refresh nodes after a node fails to respond
                sniff_on_connection_fail=settings.ELASTICSEARCH['SNIFF'],
                # and also every 60 seconds
                sniffer_timeout=60 if settings.ELASTICSEARCH['SNIFF'] else None,
            )
        except Exception as e:
            client.captureException()
            raise RuntimeError('Unable to connect to Elasticsearch cluster at "{}"'.format(self.es_url)) from e

        logger.debug('Creating queue "%s" in RabbitMQ', self.rabbit_queue_name)
        try:
            self.rabbit_connection = self.celery_app.pool.acquire(block=True)
            self.rabbit_queue = self.rabbit_connection.SimpleQueue(self.rabbit_queue_name, **settings.ELASTICSEARCH['QUEUE_SETTINGS'])
        except Exception as e:
            client.captureException()
            raise RuntimeError('Unable to create queue "{}"'.format(self.rabbit_queue_name)) from e

        self.connection_errors = self.rabbit_connection.connection_errors
        logger.debug('connection_errors set to %r', self.connection_errors)

        # TODO switch to an actual consumer based model
        # Set an upper bound to avoid fetching everything in the queue
        logger.info('Setting prefetch_count to %d', 25)
        self.rabbit_queue.consumer.qos(prefetch_count=25, apply_global=True)

        self.keep_running.set()
        logger.debug('%r successfully initialized', self)

    def start(self):
        self.initialize()
        return super().start()

    def stop(self):
        logger.info('Stopping %r...', self)
        self.keep_running.clear()
        return self.join()

    def run(self):
        num_nodes = len(self.es_client.transport.connection_pool.connections)
        logger.debug('Using %d, 1 for each ES nodes available', num_nodes)

        manager = FutureManager()

        with ThreadPoolExecutor(max_workers=num_nodes) as pool:
            while self.keep_running.is_set():

                manager.report()
                messages = self._get_messages()
                if not messages:
                    continue

                logger.debug('Recieved %d messages from RabbitMQ', len(messages))

                for chunk in util.chunked(messages, 2):
                    manager.add(pool.submit(self._index, chunk))

            manager.cancel_all()
            logger.warning('Shutting down workers for %r...', self)
        logger.warning('%r stopped.', self)

    def _get_messages(self, max_size=25, timeout=5):
        messages = []
        start = time.time()

        while self.keep_running.is_set():
            try:
                messages.append(self.rabbit_queue.get(timeout=timeout))
            except queue.Empty:
                pass

            if (time.time() - start) >= timeout or len(messages) > max_size:
                break

        return messages

    def _index(self, messages):
        with client.capture_exceptions():
            start = time.time()

            action_gen = ElasticsearchActionGenerator(self.es_indexes, messages)
            logger.debug('Indexing %d documents', len(action_gen))

            try:
                stream = helpers.streaming_bulk(
                    self.es_client,
                    action_gen,
                    max_chunk_bytes=self.MAX_CHUNK_BYTES,
                    raise_on_error=False,
                )

                for ok, resp in stream:
                    if not ok and not (resp.get('delete') and resp['delete']['status'] == 404):
                        raise ValueError(resp)
                    action_gen.ack_pending()
                action_gen.ack_pending()

                assert not action_gen.pending
                assert len(action_gen.messages) == len(action_gen.acked)
            finally:
                num = action_gen.requeue()
                if num:
                    logger.warning('Requeued %d messages', num)

            logger.info('Indexed %d documents in %.02f seconds', len(action_gen), time.time() - start)
