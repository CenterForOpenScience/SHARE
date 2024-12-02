import contextlib
import collections
from collections.abc import Callable
import dataclasses
import logging
import queue
import random
import threading
import time

import amqp.exceptions
from django.conf import settings
import kombu
from kombu.mixins import ConsumerMixin
import sentry_sdk

from share.search import (
    exceptions,
    messages,
    index_strategy,
    IndexMessenger,
)


logger = logging.getLogger(__name__)


UNPRESSURED_TIMEOUT = 1         # seconds
QUICK_TIMEOUT = 0.1             # seconds
MINIMUM_BACKOFF_FACTOR = 1.6    # unitless ratio
MAXIMUM_BACKOFF_FACTOR = 2.0    # unitless ratio
MAXIMUM_BACKOFF_TIMEOUT = 60    # seconds
CONNECTION_HEARTBEAT = 20       # seconds (see https://www.rabbitmq.com/docs/heartbeats#false-positives )


class TooFastSlowDown(Exception):
    pass


class IndexerDaemonControl:
    def __init__(self, celery_app, *, daemonthread_context=None, stop_event=None):
        self.kombu_connection = kombu.Connection(
            celery_app.conf.broker_url,  # use celery_app.conf for consistent config
            heartbeat=CONNECTION_HEARTBEAT,
        )
        self.daemonthread_context = daemonthread_context
        self._daemonthreads = []
        # shared stop_event for all threads below
        self.stop_event = stop_event or threading.Event()

    def start_daemonthreads_for_strategy(self, index_strategy):
        logger.info('starting daemon for %s', index_strategy)
        _daemon = IndexerDaemon(
            index_strategy=index_strategy,
            stop_event=self.stop_event,
            daemonthread_context=self.daemonthread_context,
        )
        # spin up daemonthreads, ready for messages
        self._daemonthreads.extend(_daemon.start())
        _consumer = KombuMessageConsumer(
            kombu_connection=self.kombu_connection.clone(),
            stop_event=self.stop_event,
            index_strategy=index_strategy,
            message_callback=_daemon.on_message,
        )
        # give the daemon a more robust callback for ack-ing
        _daemon.ack_callback = _consumer.ensure_ack
        # assign a thread for the consumer to receive and enqueue messages to this daemon
        threading.Thread(target=_consumer.run).start()
        return _daemon

    def start_all_daemonthreads(self):
        for _index_strategy in index_strategy.all_index_strategies().values():
            self.start_daemonthreads_for_strategy(_index_strategy)

    def stop_daemonthreads(self, *, wait=False):
        self.stop_event.set()  # rely on the politeness of daemons
        if wait:
            for _thread in self._daemonthreads:
                _thread.join()


class KombuMessageConsumer(ConsumerMixin):
    PREFETCH_COUNT = 7500

    should_stop: bool  # (from ConsumerMixin)

    def __init__(self, *, kombu_connection, stop_event, message_callback, index_strategy):
        self.connection = kombu_connection
        self.__stop_event = stop_event
        self.__message_callback = message_callback
        self.__index_strategy = index_strategy

    # overrides ConsumerMixin.run
    def run(self):
        logger.info('%r: Starting', self)
        # start a thread to respect the stop event
        threading.Thread(target=self.__wait_for_stop).start()
        logger.debug('%r: Delegating to Kombu.run', self)
        return super().run()

    def __wait_for_stop(self):
        while not (self.should_stop or self.__stop_event.is_set()):
            self.__stop_event.wait(timeout=UNPRESSURED_TIMEOUT)
        logger.warning('%r: Stopping', self)
        self.should_stop = True
        self.__stop_event.set()

    # for ConsumerMixin -- specifies rabbit queues to consume, registers on_message callback
    def get_consumers(self, Consumer, channel):
        index_messenger = IndexMessenger(index_strategys=[self.__index_strategy])
        queues = tuple(index_messenger.incoming_messagequeue_iter(channel))
        logger.debug('%r: Consuming from queues %r', self, queues)
        return [
            Consumer(
                queues=queues,
                callbacks=[self.__message_callback],
                accept=['json'],
                prefetch_count=self.PREFETCH_COUNT,
            )
        ]

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.__index_strategy.name)

    def consume(self, *args, **kwargs):
        # wrap `consume` in `kombu.Connection.ensure`, following guidance from
        # https://docs.celeryq.dev/projects/kombu/en/stable/userguide/failover.html#consumer
        consume = self.connection.ensure(self.connection, super().consume)
        return consume(*args, **kwargs)

    def ensure_ack(self, daemon_message: messages.DaemonMessage):
        # if the connection the message came thru is no longer usable,
        # use `kombu.Connection.autoretry` to revive it for an ack
        try:
            daemon_message.ack()
        except (ConnectionError, amqp.exceptions.ConnectionError):
            @self.connection.autoretry
            def _do_ack(*, channel):
                try:
                    channel.basic_ack(daemon_message.kombu_message.delivery_tag)
                finally:
                    channel.close()
            _do_ack()


def _default_ack_callback(daemon_message: messages.DaemonMessage) -> None:
    daemon_message.ack()


class IndexerDaemon:
    MAX_LOCAL_QUEUE_SIZE = 5000
    ack_callback: Callable[[messages.DaemonMessage], None]

    def __init__(self, index_strategy, *, stop_event=None, daemonthread_context=None):
        self.stop_event = (
            stop_event
            if stop_event is not None
            else threading.Event()
        )
        self.index_strategy = index_strategy  # TODO: error if index not ready
        self.__daemonthread_context = daemonthread_context or contextlib.nullcontext
        self.__local_message_queues = {}
        self.__started = False
        self.ack_callback = _default_ack_callback

    def start(self) -> list[threading.Thread]:
        if self.__started:
            raise exceptions.DaemonSetupError('IndexerDaemon already set up!')
        self.__started = True
        _supported_message_types = self.index_strategy.supported_message_types
        # for each type of message to be handled, one queue for incoming messages and a
        # __message_handling_loop thread that handles messages from the queue
        _loopthreads = [
            self.start_typed_loop_and_queue(message_type)
            for message_type in _supported_message_types
        ]
        return [
            *_loopthreads,

        ]

    def start_typed_loop_and_queue(self, message_type) -> threading.Thread:
        assert message_type not in self.__local_message_queues
        _queue_from_rabbit_to_daemon = queue.Queue(maxsize=self.MAX_LOCAL_QUEUE_SIZE)
        self.__local_message_queues[message_type] = _queue_from_rabbit_to_daemon
        _handling_loop = MessageHandlingLoop(
            index_strategy=self.index_strategy,
            message_type=message_type,
            stop_event=self.stop_event,
            local_message_queue=_queue_from_rabbit_to_daemon,
            log_prefix=f'{repr(self)} MessageHandlingLoop: ',
            daemonthread_context=self.__daemonthread_context,
            ack_callback=self.ack_callback,
        )
        return _handling_loop.start_thread()

    def on_message(self, body, message):
        daemon_message = messages.DaemonMessage.from_received_message(message)
        logger.debug('%s got message %s', self, daemon_message)
        local_message_queue = self.__local_message_queues.get(daemon_message.message_type)
        if local_message_queue is None:
            raise exceptions.DaemonMessageError(
                f'Received message with unsupported type "{daemon_message.message_type}"'
                f' (message: {message})'
                f' (supported message types: {self.index_strategy.supported_message_types})'
            )
        # Keep blocking on put() until there's space in the queue or it's time to stop
        while not self.stop_event.is_set():
            try:
                local_message_queue.put(daemon_message, timeout=UNPRESSURED_TIMEOUT)
                break
            except queue.Full:
                continue

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.index_strategy.name)


@dataclasses.dataclass
class MessageHandlingLoop:
    index_strategy: index_strategy.IndexStrategy
    message_type: messages.MessageType
    stop_event: threading.Event
    local_message_queue: queue.Queue
    log_prefix: str
    daemonthread_context: Callable[[], contextlib.AbstractContextManager]
    ack_callback: Callable[[messages.DaemonMessage], None]
    _leftover_daemon_messages_by_target_id = None

    def __post_init__(self):
        self._reset_backoff_timeout()

    def start_thread(self):
        _thread = threading.Thread(target=self._the_loop_itself)
        _thread.start()
        return _thread

    def _the_loop_itself(self):
        with self.daemonthread_context():
            try:
                while not self.stop_event.is_set():
                    try:
                        self._handle_some_messages()
                    except TooFastSlowDown:
                        self._back_off()
                    else:
                        self._reset_backoff_timeout()
            except Exception as e:
                sentry_sdk.capture_exception()
                logger.exception('%sEncountered an unexpected error (%s)', self.log_prefix, e)
                raise
            finally:
                self.stop_event.set()

    def _raise_if_backfill_noncurrent(self):
        if self.message_type.is_backfill:
            index_backfill = self.index_strategy.get_or_create_backfill()
            if index_backfill.specific_indexname != self.index_strategy.current_indexname:
                raise exceptions.DaemonSetupError(
                    'IndexerDaemon observes conflicting currence:'
                    f'\n\tIndexBackfill (from database) says current is "{index_backfill.specific_indexname}"'
                    f'\n\tIndexStrategy (from static code) says current is "{self.index_strategy.current_indexname}"'
                    '\n\t(may be the daemon is running old code -- will die and retry,'
                    ' but if this keeps happening you may need to reset backfill_status'
                    ' to INITIAL and restart the backfill)'
                )

    def _get_daemon_messages(self):
        daemon_messages_by_target_id = self._leftover_daemon_messages_by_target_id
        if daemon_messages_by_target_id is not None:
            self._leftover_daemon_messages_by_target_id = None
            return daemon_messages_by_target_id
        daemon_messages_by_target_id = collections.defaultdict(list)
        _chunk_size = settings.ELASTICSEARCH['CHUNK_SIZE']
        while len(daemon_messages_by_target_id) < _chunk_size and not self.stop_event.is_set():
            try:
                # If we have any messages queued up, push them through ASAP
                daemon_message = self.local_message_queue.get(timeout=(
                    QUICK_TIMEOUT
                    if daemon_messages_by_target_id
                    else UNPRESSURED_TIMEOUT
                ))
                daemon_messages_by_target_id[daemon_message.target_id].append(daemon_message)
            except queue.Empty:
                break
        return daemon_messages_by_target_id

    def _handle_some_messages(self):
        start_time = time.time()
        doc_count, error_count = 0, 0
        daemon_messages_by_target_id = self._get_daemon_messages()
        if daemon_messages_by_target_id:
            self._raise_if_backfill_noncurrent()
            messages_chunk = messages.MessagesChunk(
                message_type=self.message_type,
                target_ids_chunk=tuple(daemon_messages_by_target_id.keys()),
            )
            for message_response in self.index_strategy.pls_handle_messages_chunk(messages_chunk):
                if message_response.is_done:
                    doc_count += 1
                    logger.debug('%sHandled message: %s', self.log_prefix, message_response)
                elif message_response.status_code == 429:  # 429 Too Many Requests
                    self._leftover_daemon_messages_by_target_id = daemon_messages_by_target_id
                    raise TooFastSlowDown
                else:
                    error_count += 1
                    logger.error('%sEncountered error: %s', self.log_prefix, message_response.error_text)
                    sentry_sdk.capture_message('error handling message', extras={'message_response': message_response})
                target_id = message_response.index_message.target_id
                for daemon_message in daemon_messages_by_target_id.pop(target_id, ()):
                    self.ack_callback(daemon_message)
            if daemon_messages_by_target_id:  # should be empty by now
                logger.error('%sUnhandled messages?? %s', self.log_prefix, len(daemon_messages_by_target_id))
                sentry_sdk.capture_message(
                    'unhandled daemon messages!',
                    extras={
                        'message_type': self.message_type,
                        'target_ids': tuple(daemon_messages_by_target_id.keys()),
                    },
                )
        time_elapsed = time.time() - start_time
        if doc_count or error_count:
            logger.info('%sIndexed %d documents in %.02fs (with %d errors)', self.log_prefix, doc_count, time_elapsed, error_count)

    def _reset_backoff_timeout(self):
        self._backoff_timeout = UNPRESSURED_TIMEOUT

    def _back_off(self):
        _backoff_factor = random.uniform(MINIMUM_BACKOFF_FACTOR, MAXIMUM_BACKOFF_FACTOR)
        self._backoff_timeout = min(
            MAXIMUM_BACKOFF_TIMEOUT,
            (self._backoff_timeout * _backoff_factor),
        )
        logger.warning(f'{self.log_prefix}Backing off (pause for {self._backoff_timeout:.2} seconds)')
        _backoff_wait(stop_event=self.stop_event, backoff_timeout=self._backoff_timeout)


# helper function for easier testing of backoff logic
def _backoff_wait(*, stop_event, backoff_timeout):
    stop_event.wait(timeout=backoff_timeout)
