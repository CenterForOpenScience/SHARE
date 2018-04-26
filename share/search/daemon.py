from concurrent.futures import ThreadPoolExecutor
import logging
import queue
import time

from django.conf import settings

from kombu import Queue
from kombu.mixins import ConsumerMixin

from elasticsearch import Elasticsearch
from elasticsearch import helpers

from raven.contrib.django.raven_compat.models import client

from share import util
from share.search.indexing import ElasticsearchActionGenerator
from share.search.indexing import IndexableMessage


logger = logging.getLogger(__name__)


class SearchIndexer(ConsumerMixin):

    MAX_CHUNK_BYTES = 10 * 1024 ** 2  # 10 megs

    def __init__(self, connection, index, url=None, max_size=5000, prefetch_count=7500, stop_event=None):
        self._model_queues = {}
        self._pool = ThreadPoolExecutor(max_workers=len(settings.INDEXABLE_MODELS) + 1)
        self._queue = queue.Queue(maxsize=max_size)
        self.connection = connection
        self.es_url = url or settings.ELASTICSEARCH['URL']
        self.index = index
        self.prefetch_count = prefetch_count
        self.stop_event = stop_event

        self.es_client = Elasticsearch(
            self.es_url,
            retry_on_timeout=True,
            timeout=settings.ELASTICSEARCH['TIMEOUT'],
            # sniff before doing anything
            sniff_on_start=settings.ELASTICSEARCH['SNIFF'],
            # refresh nodes after a node fails to respond
            sniff_on_connection_fail=settings.ELASTICSEARCH['SNIFF'],
            # and also every 60 seconds
            sniffer_timeout=60 if settings.ELASTICSEARCH['SNIFF'] else None,
        )

    def run(self):
        logger.info('%r: Starting', self)

        logger.debug('%r: Starting main indexing loop', self)
        self._pool.submit(self._index_loop)

        try:
            logger.debug('%r: Delegating to Kombu.run', self)
            return super().run()
        finally:
            self.stop()

    def stop(self):
        if not self.should_stop:
            logger.warning('%r: Shutting down', self)
        self.should_stop = True
        self._pool.shutdown(wait=False)
        if self.stop_event:
            self.stop_event.set()

    def get_consumers(self, Consumer, channel):
        queue_settings = settings.ELASTICSEARCH['QUEUE_SETTINGS']
        queue_names = settings.ELASTICSEARCH['INDEXES'][self.index]
        return [
            Consumer(
                [
                    Queue(queue_names['URGENT_QUEUE'], **queue_settings),
                    Queue(queue_names['DEFAULT_QUEUE'], **queue_settings),
                ],
                callbacks=[self.on_message],
                accept=['json'],
                prefetch_count=self.prefetch_count,
            )
        ]

    def on_message(self, body, message):
        msg = IndexableMessage.wrap(message)

        if msg.model not in self._model_queues:
            self._model_queues[msg.model] = queue.Queue()
            self._pool.submit(self._action_loop, msg.model, self._model_queues[msg.model])

        self._model_queues[msg.model].put(message)

    def _action_loop(self, model, q, chunk_size=250, timeout=5):
        try:
            while not self.should_stop:
                msgs = []
                while len(msgs) < chunk_size:
                    try:
                        # If we have any messages queued up, push them through ASAP
                        msgs.append(q.get(timeout=.1 if msgs else timeout))
                    except queue.Empty:
                        break

                if not msgs:
                    logger.debug('%r: Recieved no messages to queue up', self)
                    continue

                start = time.time()
                logger.debug('%r: Preparing %d %ss to be indexed', self, len(msgs), model)
                for msg, action in zip(msgs, ElasticsearchActionGenerator([self.index], msgs)):
                    self._queue.put((msg, action))
                logger.info('%r: Prepared %d %ss to be indexed in %.02fs', self, len(msgs), model, time.time() - start)
        except Exception as e:
            client.captureException()
            logger.exception('%r: _action_loop encountered an unexpected error', self)
            self.stop()

    def _actions(self, size, msgs, timeout=5):
        for _ in range(size):
            try:
                msg, action = self._queue.get(timeout=timeout)
                if action is None:
                    msg.ack()
                    continue
                msgs.append(msg)
                yield action
            except queue.Empty:
                raise StopIteration

    def _index_loop(self):
        try:
            while not self.should_stop:
                msgs = []
                actions = self._actions(250, msgs)

                stream = helpers.streaming_bulk(
                    self.es_client,
                    actions,
                    max_chunk_bytes=self.MAX_CHUNK_BYTES,
                    raise_on_error=False,
                )

                start = time.time()
                for (ok, resp), msg in zip(stream, msgs):
                    if not ok and not (resp.get('delete') and resp['delete']['status'] == 404):
                        raise ValueError(ok, resp, msg)
                    assert len(resp.values()) == 1
                    _id = list(resp.values())[0]['_id']
                    assert msg.payload['ids'] == [util.IDObfuscator.decode_id(_id)], '{} {}'.format(msg.payload, util.IDObfuscator.decode_id(_id))
                    msg.ack()
                if len(msgs):
                    logger.info('%r: Indexed %d documents in %.02fs', self, len(msgs), time.time() - start)
                else:
                    logger.debug('%r: Recieved no messages for %.02fs', self, time.time() - start)
        except Exception as e:
            client.captureException()
            logger.exception('%r: _index_loop encountered an unexpected error', self)
            self.stop()

    def __repr__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.index)
