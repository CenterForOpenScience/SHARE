from queue import Empty
import logging
import signal
import threading
import time

from django.conf import settings

from elasticsearch import Elasticsearch

from raven.contrib.django.raven_compat.models import client

from share.search.indexing import ESIndexer


logger = logging.getLogger(__name__)


class SearchIndexerDaemon:

    def __init__(self, celery_app, url=None, index=None, max_size=500, timeout=5, flush_interval=10):
        self.app = celery_app
        self.messages = []
        self.last_flush = 0

        self.index = index or settings.ELASTICSEARCH_INDEX
        self.client = Elasticsearch(url or settings.ELASTICSEARCH_URL, retry_on_timeout=True, timeout=settings.ELASTICSEARCH_TIMEOUT)

        self.flush_interval = flush_interval
        self.max_size = max_size
        self.timeout = timeout
        self._running = threading.Event()

        if threading.current_thread() == threading.main_thread():
            logger.debug('Running in the main thread, SIGTERM is active')
            signal.signal(signal.SIGTERM, self.stop)

    def run(self):
        try:
            connection = self.app.pool.acquire(block=True)
            queue = connection.SimpleQueue(settings.ELASTIC_QUEUE, **settings.ELASTIC_QUEUE_SETTINGS)
        except Exception as e:
            logger.exception('Could not connect to broker')
            raise

        logger.info('Connected to broker')
        logger.info('Using queue "%s"', settings.ELASTIC_QUEUE)

        # Set an upper bound to avoid fetching everything in the queue
        logger.info('Setting prefetch_count to %d', self.max_size * 1.1)
        queue.consumer.qos(prefetch_count=int(self.max_size * 1.1), apply_global=True)

        try:
            self._run(queue)
        except KeyboardInterrupt:
            logger.warning('Recieved Interrupt. Exiting...')
            return
        except Exception as e:
            client.captureException()
            logger.exception('Encountered an unexpected error. Attempting to flush before exiting.')

            if self.messages:
                try:
                    self.flush()
                except Exception:
                    client.captureException()
                    logger.exception('%d messages could not be flushed', len(self.messages))

            raise e
        finally:
            try:
                queue.close()
                connection.close()
            except Exception as e:
                logger.exception('Failed to clean up broker connection')

    def stop(self):
        logger.info('Stopping indexer...')
        self._running.clear()

    def flush(self):
        logger.info('Flushing %d messages', len(self.messages))

        ESIndexer(self.client, self.index, *self.messages).index()

        self.messages.clear()
        self.last_flush = time.time()

        logger.debug('Successfully flushed messages')

    def _run(self, queue):
        self._running.set()
        self.last_flush = time.time()

        while self._running.is_set():
            try:
                message = queue.get(timeout=self.timeout)
                self.messages.append(message)
            except Empty:
                pass

            if not self.messages:
                continue

            if time.time() - self.last_flush >= self.flush_interval:
                logger.debug('Time since last flush (%.2f sec) has exceeded flush_interval (%.2f sec) . Flushing...', time.time() - self.last_flush, self.flush_interval)
                self.flush()
            elif len(self.messages) >= self.max_size:
                logger.debug('Buffer has exceeded max_size. Flushing...')
                self.flush()

        logger.info('Exiting...')
