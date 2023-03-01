import contextlib

import celery
from django.conf import settings

from share.search.messages import MessagesChunk, MessageType
from share.search.index_strategy import IndexStrategy


class IndexMessenger:
    retry_policy = {
        'interval_start': 0,  # First retry immediately,
        'interval_step': 2,   # then increase by 2s for every retry.
        'interval_max': 30,   # but don't exceed 30s between retries.
        'max_retries': 30,    # give up after 30 tries.
    }

    def __init__(self, *, celery_app=None, index_names=None):
        self.celery_app = (
            celery.current_app
            if celery_app is None
            else celery_app
        )
        self.index_strategys = (
            IndexStrategy.for_all_indexes()
            if index_names is None
            else tuple(
                IndexStrategy.by_name(index_name)
                for index_name in index_names
            )
        )

    def send_message(self, message_type: MessageType, target_id, *, urgent=False):
        self.send_messages_chunk(
            MessagesChunk(message_type, [target_id]),
            urgent=urgent,
        )

    def send_messages_chunk(self, messages_chunk: MessagesChunk, *, urgent=False):
        queue_names = (
            index_strategy.get_queue_name(urgent)
            for index_strategy in self.index_strategys
            if messages_chunk.message_type in index_strategy.supported_message_types
        )
        queue_settings = settings.ELASTICSEARCH['KOMBU_QUEUE_SETTINGS']
        with self.celery_app.pool.acquire(block=True) as connection:
            # gather all the queues in one context manager so they're all closed
            # once we're done
            with contextlib.ExitStack() as kombu_queue_contexts:
                kombu_queues = [
                    kombu_queue_contexts.enter_context(
                        connection.SimpleQueue(queue_name, **queue_settings)
                    )
                    for queue_name in queue_names
                ]
                for message_dict in messages_chunk.as_dicts():
                    for kombu_queue in kombu_queues:
                        kombu_queue.put(message_dict, retry=True, retry_policy=self.retry_policy)
