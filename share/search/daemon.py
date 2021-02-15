from concurrent.futures import ThreadPoolExecutor
import logging
import queue as local_queue
import threading
import time

from kombu import Queue as KombuQueue
from kombu.mixins import ConsumerMixin

from raven.contrib.django.raven_compat.models import client

from share.search.exceptions import DaemonSetupError, DaemonMessageError, DaemonIndexingError
from share.search.messages import IndexableMessage


logger = logging.getLogger(__name__)

LOOP_TIMEOUT = 5


class CeleryMessageConsumer(ConsumerMixin):
    PREFETCH_COUNT = 7500

    def __init__(self, celery_app, indexer_daemon, elastic_manager):
        self.connection = celery_app.pool.acquire(block=True)
        self.celery_app = celery_app
        self.__indexer_daemon = indexer_daemon
        self.__elastic_manager = elastic_manager

    # overrides ConsumerMixin.run
    def run(self):
        logger.info('%r: Starting', self)

        threading.Thread(target=self.__wait_for_stop).start()

        logger.debug('%r: Delegating to Kombu.run', self)
        return super().run()

    def __wait_for_stop(self):
        while not (self.should_stop or self.__indexer_daemon.stop_event.is_set()):
            self.__indexer_daemon.stop_event.wait(timeout=LOOP_TIMEOUT)
        logger.warning('%r: Stopping', self)
        self.should_stop = True
        self.__indexer_daemon.stop_event.set()

    # for ConsumerMixin -- specifies rabbit queues to consume, registers on_message callback
    def get_consumers(self, Consumer, channel):
        kombu_queue_settings = self.__elastic_manager.settings['KOMBU_QUEUE_SETTINGS']
        index_settings = self.__elastic_manager.settings['INDEXES'][self.__indexer_daemon.index_name]
        return [
            Consumer(
                [
                    KombuQueue(index_settings['URGENT_QUEUE'], **kombu_queue_settings),
                    KombuQueue(index_settings['DEFAULT_QUEUE'], **kombu_queue_settings),
                ],
                callbacks=[self.__indexer_daemon.on_message],
                accept=['json'],
                prefetch_count=self.PREFETCH_COUNT,
            )
        ]

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.__indexer_daemon.index_name)


class SearchIndexerDaemon:

    MAX_LOCAL_QUEUE_SIZE = 5000

    @classmethod
    def start_indexer_in_thread(cls, celery_app, stop_event, elastic_manager, index_name):
        indexer_daemon = cls(
            index_name=index_name,
            elastic_manager=elastic_manager,
            stop_event=stop_event,
        )
        indexer_daemon.start_loops_and_queues()

        consumer = CeleryMessageConsumer(celery_app, indexer_daemon, elastic_manager)
        threading.Thread(target=consumer.run).start()

    def __init__(self, index_name, elastic_manager, stop_event):
        self.index_name = index_name
        self.stop_event = stop_event
        self.__elastic_manager = elastic_manager

        self.__index_setup = self.__elastic_manager.get_index_setup(index_name)

        self.__thread_pool = None
        self.__incoming_message_queues = {}
        self.__outgoing_action_queue = None

    def stop(self):
        if not self.stop_event.is_set():
            logger.warning('%r: Stopping', self)
            self.__thread_pool.shutdown(wait=False)
            self.stop_event.set()

    @property
    def all_queues_empty(self):
        return self.__outgoing_action_queue.empty() and all(
            message_queue.empty()
            for message_queue in self.__incoming_message_queues.values()
        )

    def __wait_on_stop_event(self):
        self.stop_event.wait()
        self.stop()

    def start_loops_and_queues(self):
        if self.__thread_pool:
            raise DaemonSetupError('SearchIndexerDaemon already set up!')

        supported_message_types = self.__index_setup.supported_message_types

        self.__thread_pool = ThreadPoolExecutor(max_workers=len(supported_message_types) + 2)
        self.__thread_pool.submit(self.__wait_on_stop_event)

        # one outgoing action queue and one thread that sends those actions to elastic
        self.__outgoing_action_queue = local_queue.Queue(maxsize=self.MAX_LOCAL_QUEUE_SIZE)
        self.__thread_pool.submit(self.__outgoing_action_loop)

        # for each type of message handler, one queue for incoming messages and a
        # __incoming_message_loop thread that pulls from the queue, builds actions, and
        # pushes those actions to the outgoing action queue
        for message_type in supported_message_types:
            message_queue = local_queue.Queue(maxsize=self.MAX_LOCAL_QUEUE_SIZE)
            self.__incoming_message_queues[message_type] = message_queue
            self.__thread_pool.submit(self.__incoming_message_loop, message_type)

    def on_message(self, body, message):
        wrapped_message = IndexableMessage.wrap(message)

        message_queue = self.__incoming_message_queues.get(wrapped_message.message_type)
        if message_queue is None:
            logger.warning('%r: unknown message type "%s"', self, wrapped_message.message_type)
            raise DaemonMessageError(f'Received message with unexpected type "{wrapped_message.message_type}" (message: {message})')

        message_queue.put(wrapped_message)

    def __incoming_message_loop(self, message_type):
        try:
            log_prefix = f'{repr(self)} IncomingMessageLoop({message_type}): '
            loop = IncomingMessageLoop(
                message_queue=self.__incoming_message_queues[message_type],
                outgoing_action_queue=self.__outgoing_action_queue,
                action_generator=self.__index_setup.build_action_generator(self.index_name, message_type),
                chunk_size=self.__elastic_manager.settings['CHUNK_SIZE'],
                log_prefix=log_prefix,
            )

            while not self.stop_event.is_set():
                loop.iterate_once(self.stop_event)

        except Exception as e:
            client.captureException()
            logger.exception('%sEncountered an unexpected error (%s)', log_prefix, e)
        finally:
            self.stop()

    def __outgoing_action_loop(self):
        try:
            log_prefix = f'{repr(self)} OutgoingActionLoop: '
            loop = OutgoingActionLoop(
                action_queue=self.__outgoing_action_queue,
                elastic_manager=self.__elastic_manager,
                chunk_size=self.__elastic_manager.settings['CHUNK_SIZE'],
                log_prefix=log_prefix,
            )

            while not self.stop_event.is_set():
                loop.iterate_once()

        except Exception as e:
            client.captureException()
            logger.exception('%sEncountered an unexpected error (%s)', log_prefix, e)
        finally:
            self.stop()

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.index_name)


class IncomingMessageLoop:
    def __init__(self, message_queue, outgoing_action_queue, action_generator, chunk_size, log_prefix):
        self.message_queue = message_queue
        self.outgoing_action_queue = outgoing_action_queue
        self.action_generator = action_generator
        self.chunk_size = chunk_size
        self.log_prefix = log_prefix

        logger.info('%sStarted', self.log_prefix)

    def _get_target_id_chunk(self):
        messages_by_id = {}
        target_id_chunk = []
        while len(target_id_chunk) < self.chunk_size:
            try:
                # If we have any messages queued up, push them through ASAP
                message = self.message_queue.get(timeout=.1 if target_id_chunk else LOOP_TIMEOUT)

                if message.target_id in messages_by_id:
                    # skip processing duplicate messages in one chunk
                    message.ack()
                else:
                    messages_by_id[message.target_id] = message
                    target_id_chunk.append(message.target_id)
            except local_queue.Empty:
                break
        return target_id_chunk, messages_by_id

    def iterate_once(self, stop_event):
        target_id_chunk, messages_by_id = self._get_target_id_chunk()

        if not target_id_chunk:
            logger.debug('%sRecieved no messages to queue up', self.log_prefix)
            return

        start = time.time()
        logger.debug('%sPreparing %d docs to be indexed', self.log_prefix, len(target_id_chunk))

        success_count = 0
        # at this point, we have a chunk of messages, each with exactly one pk
        # each message should turn into one elastic action/doc
        for target_id, action in self.action_generator(target_id_chunk):
            message = messages_by_id.pop(target_id)

            # Keep blocking on put() until there's space in the queue or it's time to stop
            while not stop_event.is_set():
                try:
                    self.outgoing_action_queue.put((message, action), timeout=LOOP_TIMEOUT)
                    success_count += 1
                    break
                except local_queue.Full:
                    continue

        if messages_by_id:
            # worth noting but not stopping
            logger.warning(
                'IncomingMessageLoop: action generator skipped some target_ids!\ntarget_id_chunk: %s\nleftover_messages_by_id: %s',
                target_id_chunk,
                messages_by_id,
            )

        logger.info('%sPrepared %d docs to be indexed in %.02fs', self.log_prefix, success_count, time.time() - start)


class OutgoingActionLoop:
    # ok the thing here is that we want to wait to ack the message until
    # its action is successfully sent to elastic -- this keeps the message
    # in the rabbit queue so if something explodes, the message will be retried
    # once things recover

    # how this works now is self.action_chunk_iter makes a generator that yields actions
    # and *also* side-effects the corresponding messages into self.messages_awaiting_elastic
    # keyed by the message's target_id -- this is nice because we can use elastic's
    # streaming_bulk helper to avoid too much chunking in memory (...tho it may not make much
    # difference, depending how much the elastic helpers hold in memory) and use the _id on
    # each successful response to find and ack the respective message

    MAX_CHUNK_BYTES = 10 * 1024 ** 2  # 10 megs

    def __init__(self, action_queue, elastic_manager, chunk_size, log_prefix):
        self.action_queue = action_queue
        self.elastic_manager = elastic_manager
        self.chunk_size = chunk_size
        self.log_prefix = log_prefix

        self.messages_awaiting_elastic = {}

        logger.info('%sStarted', self.log_prefix)

    def iterate_once(self):
        start_time = time.time()
        doc_count = 0
        action_chunk = self.action_chunk_iter()
        elastic_stream = self.elastic_manager.stream_actions(action_chunk)

        for (ok, op_type, response) in elastic_stream:
            if not ok and not (op_type == 'delete' and response['status'] == 404):
                raise DaemonIndexingError(ok, response)

            message = self.messages_awaiting_elastic.pop(str(response['_id']))
            message.ack()

        time_elapsed = time.time() - start_time
        if doc_count:
            logger.info('%sIndexed %d documents in %.02fs', self.log_prefix, doc_count, time_elapsed)
        else:
            logger.debug('%sRecieved no messages for %.02fs', self.log_prefix, time_elapsed)

        if self.messages_awaiting_elastic:
            raise DaemonIndexingError(f'Messages left awaiting elastic! ¿something happened? {self.messages_awaiting_elastic}')

    def action_chunk_iter(self):
        for _ in range(self.chunk_size):
            try:
                message, action = self.action_queue.get(timeout=LOOP_TIMEOUT)
                if (
                    action is None
                    or '_id' not in action
                    or action['_id'] in self.messages_awaiting_elastic
                ):
                    message.ack()
                    continue
                self.messages_awaiting_elastic[str(action['_id'])] = message
                yield action
            except local_queue.Empty:
                raise StopIteration
