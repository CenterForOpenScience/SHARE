import contextlib
import logging
import typing
import urllib.parse

import celery
from django.conf import settings
import kombu
import kombu.simple
import requests
import sentry_sdk

from share.search.messages import MessagesChunk, MessageType
from share.search.index_strategy import IndexStrategy


logger = logging.getLogger(__name__)


class IndexMessenger:
    retry_policy = {
        'interval_start': 0,  # First retry immediately,
        'interval_step': 2,   # then increase by 2s for every retry.
        'interval_max': 30,   # but don't exceed 30s between retries.
        'max_retries': 30,    # give up after 30 tries.
    }

    def __init__(self, *, celery_app=None, index_strategys=None):
        self.celery_app = (
            celery.current_app
            if celery_app is None
            else celery_app
        )
        self.index_strategys = index_strategys or tuple(IndexStrategy.all_strategies())

    def incoming_messagequeue_iter(self, channel) -> typing.Iterable[kombu.Queue]:
        for index_strategy in self.index_strategys:
            yield kombu.Queue(channel=channel, name=index_strategy.urgent_messagequeue_name)
            yield kombu.Queue(channel=channel, name=index_strategy.nonurgent_messagequeue_name)

    def outgoing_messagequeue_iter(self, connection, message_type: MessageType, urgent: bool) -> typing.Iterable[kombu.simple.SimpleQueue]:
        for index_strategy in self.index_strategys:
            if message_type in index_strategy.supported_message_types:
                yield connection.SimpleQueue(
                    name=(
                        index_strategy.urgent_messagequeue_name
                        if urgent
                        else index_strategy.nonurgent_messagequeue_name
                    ),
                )

    def get_queue_depth(self, queue_name: str):
        try:
            rabbitmqueuerl = urllib.parse.urlunsplit((
                'http',     # scheme
                ':'.join((  # netloc (host:port)
                    settings.RABBITMQ_HOST,
                    settings.RABBITMQ_MGMT_PORT,
                )),
                '/'.join((  # path
                    'api',
                    'queues',
                    urllib.parse.quote_plus(settings.RABBITMQ_VHOST),
                    urllib.parse.quote_plus(queue_name),
                )),
                None,       # query
                None,       # fragment
            ))
            resp = requests.get(
                rabbitmqueuerl,
                auth=(settings.RABBITMQ_USERNAME, settings.RABBITMQ_PASSWORD),
            )
            return resp.json().get('messages', 0)
        except Exception:
            sentry_sdk.capture_exception()
            return '??'

    def send_message(self, message_type: MessageType, target_id, *, urgent=False):
        self.send_messages_chunk(
            MessagesChunk(message_type, [target_id]),
            urgent=urgent,
        )

    def send_messages_chunk(self, messages_chunk: MessagesChunk, *, urgent=False):
        with self._open_message_queues(messages_chunk.message_type, urgent) as message_queues:
            self._put_messages_chunk(messages_chunk, message_queues)

    def stream_message_chunks(
        self,
        message_type: MessageType,
        id_stream: typing.Iterable[int],
        *,
        chunk_size,
        urgent=False,
    ):
        with self._open_message_queues(message_type, urgent) as message_queues:
            for messages_chunk in MessagesChunk.stream_chunks(message_type, id_stream, chunk_size):
                self._put_messages_chunk(messages_chunk, message_queues)

    @contextlib.contextmanager
    def _open_message_queues(self, message_type, urgent):
        with self.celery_app.pool.acquire(block=True) as connection:
            with contextlib.ExitStack() as queue_stack:
                yield tuple(
                    queue_stack.enter_context(messagequeue)
                    for messagequeue in self.outgoing_messagequeue_iter(connection, message_type, urgent)
                )

    def _put_messages_chunk(self, messages_chunk, message_queues):
        for message_dict in messages_chunk.as_dicts():
            for message_queue in message_queues:
                message_queue.put(message_dict, retry=True, retry_policy=self.retry_policy)
