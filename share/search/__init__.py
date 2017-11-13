from django.conf import settings


class SearchIndexer:

    retry_policy = {
        'interval_start': 0,  # First retry immediately,
        'interval_step': 2,   # then increase by 2s for every retry.
        'interval_max': 30,   # but don't exceed 30s between retries.
        'max_retries': 30,    # give up after 30 tries.
    }

    def __init__(self, celery_app):
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

        with self.app.pool.acquire(block=True) as connection:
            for index in indexes:
                q = dict(settings.ELASTICSEARCH['INDEXES'][index]['QUEUE'])
                q.pop('consumer_arguments', None)
                with connection.SimpleQueue(q.pop('name'), **q) as queue:
                    for pk in pks:
                        queue.put({'version': 1, 'model': name, 'ids': [pk]}, retry=True, retry_policy=self.retry_policy)
