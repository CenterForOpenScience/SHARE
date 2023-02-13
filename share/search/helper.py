import logging
from contextlib import ExitStack

from django.conf import settings

from share.search import messages
from share.search.index_setup import IndexSetup


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
            self.index_setups = IndexSetup.all_indexes()
        else:
            self.index_setups = tuple(
                IndexSetup.by_name(index_name)
                for index_name in index_names
            )

    def send_messages(self, message_type, target_ids_chunk, urgent=False):
        # gather the queues to send to, based on the index setups' supported message types
        queue_names = [
            (
                index_setup.urgent_queue_name
                if urgent
                else index_setup.default_queue_name
            )
            for index_setup in self.index_setups
            if message_type in index_setup.supported_message_types
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
        for index_setup in self.index_setups:
            if message_type not in index_setup.supported_message_types:
                logger.error(f'skipping: {index_setup.index_name} does not support {message_type}')
                continue
            for result in index_setup.pls_handle_messages(message_type, messages_chunk):
                if not result.is_handled:
                    logger.error(
                        'error in %s handling message %s: %s',
                        (index_setup, result.daemon_message, result.error_message),
                    )
                else:
                    logger.info(
                        'success! %s handled message %s',
                        (index_setup, result.daemon_message),
                    )
