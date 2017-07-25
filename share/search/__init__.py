from django.conf import settings
from share import util


class SearchIndexer:

    retry_policy = {
        'interval_start': 0,  # First retry immediately,
        'interval_step': 2,   # then increase by 2s for every retry.
        'interval_max': 30,   # but don't exceed 30s between retries.
        'max_retries': 30,    # give up after 30 tries.
    }

    def __init__(self, celery_app):
        self.app = celery_app

    def index(self, model, *pks, queue=settings.ELASTICSEARCH['DEFAULT_QUEUE']):
        name = settings.INDEXABLE_MODELS.get(model.lower())

        if not name:
            raise ValueError('{} is not an indexable model'.format(model))

        if not pks:
            return

        with self.app.pool.acquire(block=True) as connection:
            with connection.SimpleQueue(queue, **settings.ELASTICSEARCH['QUEUE_SETTINGS']) as queue:
                for chunk in util.chunked(pks, 500):
                    if not chunk:
                        continue
                    queue.put({'version': 1, 'model': name, 'ids': pks}, retry=True, retry_policy=self.retry_policy)
