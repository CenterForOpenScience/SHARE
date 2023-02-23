import logging
from contextlib import ExitStack

from django.conf import settings

from share.search import messages
from share.search.index_strategy import IndexStrategy


__all__ = ('SearchHelper',)


logger = logging.getLogger(__name__)


class SearchHelper:

    retry_policy = {
        'interval_start': 0,  # First retry immediately,
        'interval_step': 2,   # then increase by 2s for every retry.
        'interval_max': 30,   # but don't exceed 30s between retries.
        'max_retries': 30,    # give up after 30 tries.
    }

    def __init__(self, celery_app=None, index_names=None):
        if celery_app is None:
            import celery
            self.celery_app = celery.current_app
        else:
            self.celery_app = celery_app
        if index_names is None:
            self.index_strategys = IndexStrategy.all_indexes()
        else:
            self.index_strategys = tuple(
                IndexStrategy.by_name(index_name)
                for index_name in index_names
            )

    def send_messages(self, message_type, target_ids_chunk, *, urgent=False, index_names=None):
        # gather the queues to send to, based on the index setups' supported message types
        queue_names = [
            (
                index_strategy.urgent_queue_name
                if urgent
                else index_strategy.default_queue_name
            )
            for index_strategy in self.index_strategys
            if (index_names is None or index_strategy.name in index_names)
            and (message_type in index_strategy.supported_message_types)

        ]
        queue_settings = settings.ELASTICSEARCH['KOMBU_QUEUE_SETTINGS']
        messages_chunk = messages.DaemonMessage.from_values(message_type, target_ids_chunk)
        with self.celery_app.pool.acquire(block=True) as connection:
            # gather all the queues in one context manager so they're all closed
            # once we're done
            with ExitStack() as kombu_queue_contexts:
                kombu_queues = [
                    kombu_queue_contexts.enter_context(
                        connection.SimpleQueue(queue_name, **queue_settings)
                    )
                    for queue_name in queue_names
                ]
                for message in messages_chunk:
                    for kombu_queue in kombu_queues:
                        kombu_queue.put(message.to_dict(), retry=True, retry_policy=self.retry_policy)

    def handle_messages_sync(self, message_type, target_ids):
        messages_chunk = messages.DaemonMessage.from_values(message_type, target_ids)
        for index_strategy in self.index_strategys:
            if message_type not in index_strategy.supported_message_types:
                logger.error(f'skipping: {index_strategy.name} does not support {message_type}')
                continue
            for result in index_strategy.pls_handle_messages(message_type, messages_chunk):
                if not result.is_handled:
                    logger.error(
                        'error in %s handling message %s: %s',
                        (index_strategy, result.daemon_message, result.error_message),
                    )
                else:
                    logger.info(
                        'success! %s handled message %s',
                        (index_strategy, result.daemon_message),
                    )
