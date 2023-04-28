from concurrent.futures import ThreadPoolExecutor
import contextlib
import collections
import logging
import queue as local_queue
import random
import threading
import time

from django.conf import settings
from kombu.mixins import ConsumerMixin
from raven.contrib.django.raven_compat.models import client as sentry_client

from share.search import exceptions, messages, IndexStrategy, IndexMessenger


logger = logging.getLogger(__name__)


UNPRESSURED_TIMEOUT = 1         # seconds
QUICK_TIMEOUT = 0.1             # seconds
MINIMUM_BACKOFF_FACTOR = 1.6    # unitless ratio
MAXIMUM_BACKOFF_FACTOR = 2.0    # unitless ratio
MAXIMUM_BACKOFF_TIMEOUT = 60    # seconds


class TooFastSlowDown(Exception):
    pass


class CeleryMessageConsumer(ConsumerMixin):
    PREFETCH_COUNT = 7500

    def __init__(self, celery_app, indexer_daemon, index_strategy):
        self.connection = celery_app.pool.acquire(block=True)
        self.celery_app = celery_app
        self.__indexer_daemon = indexer_daemon
        self.__index_strategy = index_strategy

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
        index_messenger = IndexMessenger(index_strategys=[self.__index_strategy])
        queues = tuple(index_messenger.incoming_messagequeue_iter(channel))
        logger.debug('%r: Consuming from queues %r', self, queues)
        return [
            Consumer(
                queues=queues,
                callbacks=[self.__indexer_daemon.on_message],
                accept=['json'],
                prefetch_count=self.PREFETCH_COUNT,
            )
        ]

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.__index_strategy.name)


class IndexerDaemon:
    MAX_LOCAL_QUEUE_SIZE = 5000

    @classmethod
    def start_daemonthreads(cls, celery_app, *, daemonthread_context=None) -> threading.Event:
        stop_event = threading.Event()
        for index_strategy in IndexStrategy.all_strategies():
            indexer_daemon = cls(
                index_strategy=index_strategy,
                stop_event=stop_event,
                daemonthread_context=daemonthread_context,
            )
            indexer_daemon.start_loops_and_queues()
            consumer = CeleryMessageConsumer(celery_app, indexer_daemon, index_strategy)
            threading.Thread(target=consumer.run).start()
        return stop_event

    def __init__(self, index_strategy, stop_event, *, daemonthread_context=None):
        self.stop_event = stop_event
        self.__index_strategy = index_strategy  # TODO: error if index not ready
        self.__daemonthread_context = daemonthread_context or contextlib.nullcontext
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
            raise exceptions.DaemonSetupError('IndexerDaemon already set up!')
        supported_message_types = self.__index_strategy.supported_message_types
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
                local_message_queue.put(daemon_message, timeout=UNPRESSURED_TIMEOUT)
                break
            except local_queue.Full:
                continue

    def __message_handling_loop(self, message_type):
        with self.__daemonthread_context():
            try:
                log_prefix = f'{repr(self)} MessageHandlingLoop: '
                loop = MessageHandlingLoop(
                    index_strategy=self.__index_strategy,
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
        return '<{}({})>'.format(self.__class__.__name__, self.__index_strategy.name)


class MessageHandlingLoop:
    def __init__(self, index_strategy, message_type, local_message_queue, stop_event, log_prefix):
        self.index_strategy = index_strategy
        self.message_type = message_type
        self.local_message_queue = local_message_queue
        self.log_prefix = log_prefix
        self.stop_event = stop_event
        self.chunk_size = settings.ELASTICSEARCH['CHUNK_SIZE']
        self._leftover_daemon_messages_by_target_id = None
        logger.info('%sStarted', self.log_prefix)

    def iterate_once(self):
        try:
            self._iterate_once()
        except TooFastSlowDown:
            self._back_off()

    def _get_daemon_messages(self):
        daemon_messages_by_target_id = self._leftover_daemon_messages_by_target_id
        if daemon_messages_by_target_id is not None:
            self._leftover_daemon_messages_by_target_id = None
            return daemon_messages_by_target_id
        daemon_messages_by_target_id = collections.defaultdict(list)
        while len(daemon_messages_by_target_id) < self.chunk_size:
            try:
                # If we have any messages queued up, push them through ASAP
                daemon_message = self.local_message_queue.get(timeout=(
                    QUICK_TIMEOUT
                    if daemon_messages_by_target_id
                    else UNPRESSURED_TIMEOUT
                ))
                daemon_messages_by_target_id[daemon_message.target_id].append(daemon_message)
            except local_queue.Empty:
                break
        return daemon_messages_by_target_id

    def _iterate_once(self):
        # each message corresponds to one action on this daemon's index
        start_time = time.time()
        doc_count, error_count = 0, 0
        daemon_messages_by_target_id = self._get_daemon_messages()
        if daemon_messages_by_target_id:
            messages_chunk = messages.MessagesChunk(
                message_type=self.message_type,
                target_ids_chunk=tuple(daemon_messages_by_target_id.keys()),
            )
            for message_response in self.index_strategy.pls_handle_messages_chunk(messages_chunk):
                if message_response.is_done:
                    doc_count += 1
                elif message_response.status_code == 429:  # 429 Too Many Requests
                    self._leftover_daemon_messages_by_target_id = daemon_messages_by_target_id
                    raise TooFastSlowDown
                else:
                    error_count += 1
                    logger.error('%sEncountered error: %s', self.log_prefix, message_response.error_label)
                    sentry_client.captureMessage('error handling message', data=message_response.error_label)
                target_id = message_response.index_message.target_id
                for daemon_message in daemon_messages_by_target_id.pop(target_id):
                    daemon_message.ack()  # finally set it free
            if daemon_messages_by_target_id:  # should be empty by now
                logger.error('%sUnhandled messages?? %s', self.log_prefix, daemon_messages_by_target_id)
                sentry_client.captureMessage('unhandled daemon messages??', data=daemon_messages_by_target_id)
        time_elapsed = time.time() - start_time
        if doc_count:
            logger.info('%sIndexed %d documents in %.02fs', self.log_prefix, doc_count, time_elapsed)
        else:
            logger.debug('%sRecieved no messages for %.02fs', self.log_prefix, time_elapsed)
        if error_count:
            logger.error('%sEncountered %d errors!', self.log_prefix, error_count)

    def _back_off(self):
        last_backoff_timeout = getattr(self, '__last_backoff_timeout', UNPRESSURED_TIMEOUT)
        backoff_timeout = min(
            MAXIMUM_BACKOFF_TIMEOUT,
            last_backoff_timeout * random.uniform(MINIMUM_BACKOFF_FACTOR, MAXIMUM_BACKOFF_FACTOR),
        )
        self.__last_backoff_timeout = backoff_timeout
        logger.warning(f'{self.log_prefix}Backing off (pause for {backoff_timeout:.2} seconds)')
        self.stop_event.wait(timeout=backoff_timeout)

    def __repr__(self):
        return f'{self.__class__.__name__}("{self.index_strategy.name}", {repr(self.message_type)})'
