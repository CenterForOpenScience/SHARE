from concurrent.futures import ThreadPoolExecutor
import logging
import queue as local_queue
import threading
import time

from django.conf import settings
from kombu import Queue as KombuQueue
from kombu.mixins import ConsumerMixin
from raven.contrib.django.raven_compat.models import client as sentry_client

from share.search import exceptions, messages, IndexSetup


logger = logging.getLogger(__name__)

UNPRESSURED_TIMEOUT = 5     # five seconds
QUICK_TIMEOUT = 0.1         # one tenth of one second


class CeleryMessageConsumer(ConsumerMixin):
    PREFETCH_COUNT = 7500

    def __init__(self, celery_app, indexer_daemon, index_setup):
        self.connection = celery_app.pool.acquire(block=True)
        self.celery_app = celery_app
        self.__indexer_daemon = indexer_daemon
        self.__index_setup = index_setup

    # overrides ConsumerMixin.run
    def run(self):
        logger.info('%r: Starting', self)
        threading.Thread(target=self.__wait_for_stop).start()
        logger.debug('%r: Delegating to Kombu.run', self)
        return super().run()

    def __wait_for_stop(self):
        while not (self.should_stop or self.__indexer_daemon.stop_event.is_set()):
            self.__indexer_daemon.stop_event.wait(timeout=UNPRESSURED_TIMEOUT)
        logger.warning('%r: Stopping', self)
        self.should_stop = True
        self.__indexer_daemon.stop_event.set()

    # for ConsumerMixin -- specifies rabbit queues to consume, registers on_message callback
    def get_consumers(self, Consumer, channel):
        kombu_queue_settings = settings.ELASTICSEARCH['KOMBU_QUEUE_SETTINGS']
        return [
            Consumer(
                [
                    KombuQueue(self.__index_setup.urgent_queue_name, **kombu_queue_settings),
                    KombuQueue(self.__index_setup.default_queue_name, **kombu_queue_settings),
                ],
                callbacks=[self.__indexer_daemon.on_message],
                accept=['json'],
                prefetch_count=self.PREFETCH_COUNT,
            )
        ]

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.__index_setup.index_name)


class IndexMessengerDaemon:
    MAX_LOCAL_QUEUE_SIZE = 5000

    @classmethod
    def start_daemonthreads(cls, celery_app, stop_event):
        for index_setup in IndexSetup.all_indexes():
            indexer_daemon = cls(index_setup=index_setup, stop_event=stop_event)
            indexer_daemon.start_loops_and_queues()
            consumer = CeleryMessageConsumer(celery_app, indexer_daemon, index_setup)
            threading.Thread(target=consumer.run).start()

    def __init__(self, index_setup, stop_event):
        self.stop_event = stop_event
        self.__index_setup = index_setup  # TODO: error if index not ready
        self.__thread_pool = None
        self.__local_message_queues = {}

    def stop(self):
        logger.warning('%r: Stopping', self)
        self.__thread_pool.shutdown(wait=False)
        self.stop_event.set()

    def __wait_on_stop_event(self):
        self.stop_event.wait()
        self.stop()

    def start_loops_and_queues(self):
        if self.__thread_pool:
            raise exceptions.DaemonSetupError('IndexMessengerDaemon already set up!')

        supported_message_types = self.__index_setup.supported_message_types

        self.__thread_pool = ThreadPoolExecutor(max_workers=len(supported_message_types) + 1)
        self.__thread_pool.submit(self.__wait_on_stop_event)

        # for each type of message to be handled, one queue for incoming messages and a
        # __message_handling_loop thread that handles messages from the queue
        for message_type in supported_message_types:
            local_message_queue = local_queue.Queue(maxsize=self.MAX_LOCAL_QUEUE_SIZE)
            self.__local_message_queues[message_type] = local_message_queue
            self.__thread_pool.submit(self.__message_handling_loop, message_type)

    def on_message(self, body, message):
        daemon_message = messages.DaemonMessage.from_received_message(message)
        local_message_queue = self.__local_message_queues.get(daemon_message.message_type)
        if local_message_queue is None:
            logger.warning('%r: unknown message type "%s"', self, daemon_message.message_type)
            raise exceptions.DaemonMessageError(f'Received message with unexpected type "{daemon_message.message_type}" (message: {message})')
        # Keep blocking on put() until there's space in the queue or it's time to stop
        while not self.stop_event.is_set():
            try:
                local_message_queue.put(message, timeout=UNPRESSURED_TIMEOUT)
                break
            except local_queue.Full:
                continue

    def __message_handling_loop(self, message_type):
        try:
            log_prefix = f'{repr(self)} MessageHandlingLoop: '
            loop = MessageHandlingLoop(
                index_setup=self.__index_setup,
                message_type=message_type,
                local_message_queue=self.__local_message_queues[message_type],
                stop_event=self.stop_event,
                log_prefix=log_prefix,
            )
            while not self.stop_event.is_set():
                loop.iterate_once()
        except Exception as e:
            sentry_client.captureException()
            logger.exception('%sEncountered an unexpected error (%s)', log_prefix, e)
        finally:
            self.stop()

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.__index_setup.index_name)


class MessageHandlingLoop:
    def __init__(self, index_setup, message_type, local_message_queue, stop_event, log_prefix):
        self.index_setup = index_setup
        self.message_type = message_type
        self.local_message_queue = local_message_queue
        self.log_prefix = log_prefix
        self.stop_event = stop_event
        self.chunk_size = settings.ELASTICSEARCH['CHUNK_SIZE']
        logger.info('%sStarted', self.log_prefix)

    def _get_messages_chunk(self):
        messages_chunk = set()
        while len(messages_chunk) < self.chunk_size:
            try:
                # If we have any messages queued up, push them through ASAP
                daemon_message = self.local_message_queue.get(timeout=(
                    QUICK_TIMEOUT
                    if messages_chunk
                    else UNPRESSURED_TIMEOUT
                ))
                if daemon_message in messages_chunk:
                    # skip processing duplicate messages in one chunk
                    daemon_message.ack()
                else:
                    messages_chunk.add(daemon_message)
            except local_queue.Empty:
                break
        return messages_chunk

    def iterate_once(self):
        # each message corresponds to one action on this daemon's index
        start_time = time.time()
        doc_count, error_count = 0, 0
        messages_chunk = self._get_messages_chunk()
        unhandled_messages = set(messages_chunk)  # copy
        if unhandled_messages:
            for message_response in self.index_setup.pls_handle_messages(self.message_type, messages_chunk):
                if message_response.daemon_message not in unhandled_messages:
                    raise exceptions.DaemonMessageError(f'where did this message come from {message_response.daemon_message}')
                unhandled_messages.remove(message_response.daemon_message)
                if message_response.is_handled:
                    doc_count += 1
                else:
                    error_count += 1
                    logger.error('%sEncountered error: %s', self.log_prefix, message_response.error_message)
                    sentry_client.captureMessage(message_response.error_message)
                message_response.daemon_message.ack()  # finally set it free
        time_elapsed = time.time() - start_time
        if doc_count:
            logger.info('%sIndexed %d documents in %.02fs', self.log_prefix, doc_count, time_elapsed)
        else:
            logger.debug('%sRecieved no messages for %.02fs', self.log_prefix, time_elapsed)
        if error_count:
            logger.error('%sEncountered %d errors!', self.log_prefix, error_count)
