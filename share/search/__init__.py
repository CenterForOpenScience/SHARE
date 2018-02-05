from django.conf import settings
from django.db.models import Q

from share.models import AbstractCreativeWork


class SearchIndexer:

    retry_policy = {
        'interval_start': 0,  # First retry immediately,
        'interval_step': 2,   # then increase by 2s for every retry.
        'interval_max': 30,   # but don't exceed 30s between retries.
        'max_retries': 30,    # give up after 30 tries.
    }

    def __init__(self, celery_app=None):
        if celery_app is None:
            import celery
            self.app = celery.current_app
        else:
            self.app = celery_app

    def index(self, model, *pks, index=None):
        name = settings.INDEXABLE_MODELS.get(model.lower())

        if index is None:
            indexes = settings.ELASTICSEARCH['ACTIVE_INDEXES']
        else:
            indexes = [index]

        if not name:
            raise ValueError('{} is not an indexable model'.format(model))

        if not pks:
            return

        pks = self.pks_to_reindex(model, pks)

        with self.app.pool.acquire(block=True) as connection:
            for index in indexes:
                q = dict(settings.ELASTICSEARCH['INDEXES'][index]['QUEUE'])
                q.pop('consumer_arguments', None)
                with connection.SimpleQueue(q.pop('name'), **q) as queue:
                    for pk in pks:
                        queue.put({'version': 1, 'model': name, 'ids': [pk]}, retry=True, retry_policy=self.retry_policy)

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
                ) |
                Q(
                    outgoing_creative_work_relations__type=parent_relation,
                    outgoing_creative_work_relations__related__outgoing_creative_work_relations__type=parent_relation,
                    outgoing_creative_work_relations__related__outgoing_creative_work_relations__related_id__in=pks
                ) |
                Q(
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
