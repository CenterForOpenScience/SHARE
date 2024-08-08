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

from share.models import FeatureFlag
from share.search.messages import MessagesChunk, MessageType
from share.search import index_strategy


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
        self.index_strategys = index_strategys or tuple(index_strategy.all_index_strategies().values())

    def notify_indexcard_update(self, indexcards, *, urgent=False):
        self.send_messages_chunk(
            MessagesChunk(
                MessageType.UPDATE_INDEXCARD,
                [
                    _indexcard.id
                    for _indexcard in indexcards
                ],
            ),
            urgent=urgent,
        )
        if FeatureFlag.objects.flag_is_up(FeatureFlag.IGNORE_SHAREV2_INGEST):
            # for back-compat:
            self.notify_suid_update(
                [
                    _indexcard.source_record_suid_id
                    for _indexcard in indexcards
                ],
                urgent=urgent,
            )

    def notify_suid_update(self, suid_ids, *, urgent=False):
        self.send_messages_chunk(
            MessagesChunk(MessageType.INDEX_SUID, suid_ids),
            urgent=urgent,
        )

    def incoming_messagequeue_iter(self, channel) -> typing.Iterable[kombu.Queue]:
        for _index_strategy in self.index_strategys:
            yield kombu.Queue(channel=channel, name=_index_strategy.urgent_messagequeue_name)
            yield kombu.Queue(channel=channel, name=_index_strategy.nonurgent_messagequeue_name)

    def outgoing_messagequeue_iter(self, connection, message_type: MessageType, urgent: bool) -> typing.Iterable[kombu.simple.SimpleQueue]:
        for _index_strategy in self.index_strategys:
            if message_type in _index_strategy.supported_message_types:
                yield connection.SimpleQueue(
                    name=(
                        _index_strategy.urgent_messagequeue_name
                        if urgent
                        else _index_strategy.nonurgent_messagequeue_name
                    ),
                )

    def get_queue_stats(self, queue_name: str):
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
                'msg_rates_age=30&msg_rates_incr=30',  # get avg rates over 30 seconds
                None,       # fragment
            ))
            resp = requests.get(
                rabbitmqueuerl,
                auth=(settings.RABBITMQ_USERNAME, settings.RABBITMQ_PASSWORD),
            )
            _resp_json = resp.json()
            try:
                return {
                    'queue_depth': _resp_json['messages'],
                    'avg_ack_rate': int(_resp_json['message_stats']['ack_details']['avg_rate']),
                }
            except KeyError:
                return {
                    'queue_depth': '??',
                    'avg_ack_rate': '??',
                }
        except Exception:
            sentry_sdk.capture_exception()
            return {
                'queue_depth': '??',
                'avg_ack_rate': '??',
            }

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
                logger.debug('putting %s into %s', message_dict, message_queue.queue)
                message_queue.put(message_dict, retry=True, retry_policy=self.retry_policy)
