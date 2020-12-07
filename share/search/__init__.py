from contextlib import ExitStack

from django.apps import apps
from django.db.models import Q

from share.models import AbstractCreativeWork
from share.search.elastic_manager import ElasticManager
from share.search.messages import MessageType


__all__ = ('SearchIndexer', 'MessageType')


class SearchIndexer:

    retry_policy = {
        'interval_start': 0,  # First retry immediately,
        'interval_step': 2,   # then increase by 2s for every retry.
        'interval_max': 30,   # but don't exceed 30s between retries.
        'max_retries': 30,    # give up after 30 tries.
    }

    def __init__(self, celery_app=None, elastic_manager=None):
        self.elastic_manager = elastic_manager or ElasticManager()

        if celery_app is None:
            import celery
            self.app = celery.current_app
        else:
            self.app = celery_app

    def send_messages(self, message_type, target_ids, urgent=False, index_names=None):
        if not index_names:
            index_names = self.elastic_manager.settings['ACTIVE_INDEXES']

        messages = (
            {
                'version': 2,
                'message_type': message_type.value,
                'target_id': target_id,
            }
            for target_id in target_ids
        )

        # gather the queues to send to, based on the index setups' supported message types
        queue_key = 'URGENT_QUEUE' if urgent else 'DEFAULT_QUEUE'
        queue_names = [
            self.elastic_manager.settings['INDEXES'][index_name][queue_key]
            for index_name in index_names
            if message_type in self.elastic_manager.get_index_setup(index_name).supported_message_types
        ]
        queue_settings = self.elastic_manager.settings['KOMBU_QUEUE_SETTINGS']

        with self.app.pool.acquire(block=True) as connection:
            # gather all the queues in one context manager so they're all closed
            # once we're done
            with ExitStack() as kombu_queue_contexts:
                kombu_queues = [
                    kombu_queue_contexts.enter_context(
                        connection.SimpleQueue(queue_name, **queue_settings)
                    )
                    for queue_name in queue_names
                ]

                for message in messages:
                    for kombu_queue in kombu_queues:
                        kombu_queue.put(message, retry=True, retry_policy=self.retry_policy)

    def handle_messages_sync(self, message_type, target_ids, index_names=None):
        if not index_names:
            index_names = self.elastic_manager.settings['ACTIVE_INDEXES']

        for index_name in index_names:
            index_setup = self.elastic_manager.get_index_setup(index_name)
            action_generator = index_setup.build_action_generator(index_name, message_type)
            elastic_actions = [
                elastic_action
                for (_, elastic_action) in action_generator(target_ids)
            ]
            self.elastic_manager.send_actions_sync(elastic_actions)
        self.elastic_manager.refresh_indexes(index_names)

    # consider the below deprecated -- should be removed along with ShareObject
    def index(self, model_name, *pks, index=None, urgent=False):
        message_type = {
            'agent': MessageType.INDEX_AGENT,
            'creativework': MessageType.INDEX_CREATIVEWORK,
            'subject': MessageType.INDEX_SUBJECT,
            'tag': MessageType.INDEX_TAG,
        }[model_name.lower()]

        if not pks:
            return

        model = apps.get_model('share', model_name)
        pks = self.pks_to_reindex(model, pks)

        self.send_messages(
            message_type=message_type,
            target_ids=pks,
            urgent=urgent,
            index_names=[index] if index else None,
        )

    def pks_to_reindex(self, model, pks):
        """Get all pks that should be reindexed if the objects with the given ids were updated.

        The indexed payload may include related objects, which we don't want to get stale.
        """
        pks = set(pks)
        if model is AbstractCreativeWork:
            # Reindex children/gchildren/ggchildren of any affected works
            parent_relation = 'share.ispartof'
            children = model.objects.filter((
                Q(
                    outgoing_creative_work_relations__type=parent_relation,
                    outgoing_creative_work_relations__related_id__in=pks
                ) | Q(
                    outgoing_creative_work_relations__type=parent_relation,
                    outgoing_creative_work_relations__related__outgoing_creative_work_relations__type=parent_relation,
                    outgoing_creative_work_relations__related__outgoing_creative_work_relations__related_id__in=pks
                ) | Q(
                    outgoing_creative_work_relations__type=parent_relation,
                    outgoing_creative_work_relations__related__outgoing_creative_work_relations__type=parent_relation,
                    outgoing_creative_work_relations__related__outgoing_creative_work_relations__related__outgoing_creative_work_relations__type=parent_relation,
                    outgoing_creative_work_relations__related__outgoing_creative_work_relations__related__outgoing_creative_work_relations__related_id__in=pks
                )),
                is_deleted=False
            ).values_list('id', flat=True)

            # Reindex works retracted by any affected works
            retraction_relation = 'share.retracts'
            retracted = model.objects.filter(
                incoming_creative_work_relations__type=retraction_relation,
                incoming_creative_work_relations__subject_id__in=pks,
                is_deleted=False
            ).values_list('id', flat=True)

            return pks.union(children, retracted)
        return pks
