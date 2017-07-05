from django.conf import settings


class SearchIndexer:

    retry_policy = {
        'interval_start': 0,  # First retry immediately,
        'interval_step': 2,   # then increase by 2s for every retry.
        'interval_max': 30,   # but don't exceed 30s between retries.
        'max_retries': 30,    # give up after 30 tries.
    }

    models = {
        'creativework': 'CreativeWork'
    }

    def __init__(self, celery_app):
        self.app = celery_app

    def index(self, model, *pks):
        name = self.models.get(model.lower())

        if not name:
            raise ValueError('{} is not an indexable model'.format(model))

        if not pks:
            return

        with self.app.pool.acquire(block=True) as connection:
            with connection.SimpleQueue(settings.ELASTIC_QUEUE, **settings.ELASTIC_QUEUE_SETTINGS) as queue:
                queue.put({name: pks}, retry=True, retry_policy=self.retry_policy)
