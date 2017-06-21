import logging
import time
from queue import Empty

from django.conf import settings

from share import util

from bots.elasticsearch.tasks import index_model


logger = logging.getLogger(__name__)


class SearchIndexerDaemon:

    def __init__(self, celery_app, max_size=500, timeout=5, flush_interval=10):
        self.app = celery_app
        self.messages = []
        self.last_flush = 0

        self.flush_interval = flush_interval
        self.max_size = max_size
        self.timeout = timeout
        self._running = False

        self.sentry = None
        if hasattr(settings, 'RAVEN_CONFIG') and settings.RAVEN_CONFIG['dsn']:
            logger.info('Sentry is active')
            import raven
            self.sentry = raven.Client(settings.RAVEN_CONFIG['dsn'])

    def run(self):
        try:
            connection = self.app.pool.acquire(block=True)
            queue = connection.SimpleQueue(settings.ELASTIC_QUEUE, **settings.ELASTIC_QUEUE_SETTINGS)
        except Exception as e:
            logger.exception('Could not connect to broker')
            raise

        logger.info('Connected to broker')
        logger.info('Using queue "%s"', settings.ELASTIC_QUEUE)

        try:
            self._run(queue)
        except KeyboardInterrupt:
            logger.warning('Recieved Interrupt. Exiting...')
            return
        except Exception as e:
            logger.exception('Encountered an unexpected error. Attempting to flush before exiting.')

            if self.sentry:
                self.sentry.captureException()

            if self.messages:
                try:
                    self.flush()
                except Exception:
                    logger.exception('%d messages could not be flushed', len(self.messages))
                    if self.sentry:
                        self.sentry.captureException()
            raise e
        finally:
            try:
                queue.close()
                connection.close()
            except Exception as e:
                logger.exception('Failed to clean up broker connection')

    def flush(self):
        logger.info('Flushing %d messages', len(self.messages))

        try:
            # TODO Move search logic into this module
            # TODO Support more than just creativeworks?
            buf = []
            for message in self.messages:
                buf.extend(message.payload['CreativeWork'])

            logger.debug('Sending %d works to Elasticsearch', len(buf))
            for chunk in util.chunked(buf, size=500):
                index_model('CreativeWork', buf)
        except Exception as e:
            logger.exception('Failed to index works')
            raise
        else:
            logger.debug('Works successfully indexed')

        errors = []
        logger.debug('ACKing received messages')
        for message in self.messages:
            try:
                message.ack()
            except Exception as e:
                logger.exception('Could not ACK %r', message)
                errors.append(e)
        logger.debug('Messages successfully ACKed')

        self.messages.clear()
        self.last_flush = time.time()

        if errors:
            logger.error('Encounted %d errors while attempting to ACK messages', len(errors))
            raise errors[0]
        logger.debug('Successfully flushed messages')

    def _run(self, queue):
        self._running = True
        self.last_flush = time.time()

        while self._running:
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
