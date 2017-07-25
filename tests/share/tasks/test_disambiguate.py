import pytest
from queue import Empty

from django.apps import apps
from django.conf import settings

from tests import factories


@pytest.mark.django_db
class TestDisambiguate:

    def test_elastic_queue(self, celery_app):
        nd = factories.NormalizedDataFactory(data={
            '@graph': [{
                '@id': '_:1234',
                '@type': 'creativework',
                'title': 'All About Tamanduas',
            }]
        }, source__is_trusted=True)

        with celery_app.pool.acquire(block=True) as connection:
            with connection.SimpleQueue(settings.ELASTIC_QUEUE, **settings.ELASTIC_QUEUE_SETTINGS) as queue:
                queue.clear()

                celery_app.tasks['share.tasks.disambiguate'](nd.id)

                message = queue.get(timeout=5)
                assert len(apps.get_model('share', message.payload['model']).objects.filter(id__in=message.payload['ids'])) == len(message.payload['ids'])

    def test_elastic_queue_only_works(self, celery_app):
        nd = factories.NormalizedDataFactory(data={
            '@graph': [{
                '@id': '_:1234',
                '@type': 'person',
                'given_name': 'Jane',
                'family_name': 'Doe',
            }]
        }, source__is_trusted=True)

        with celery_app.pool.acquire(block=True) as connection:
            with connection.SimpleQueue(settings.ELASTIC_QUEUE, **settings.ELASTIC_QUEUE_SETTINGS) as queue:
                queue.clear()

                celery_app.tasks['share.tasks.disambiguate'](nd.id)

                with pytest.raises(Empty):
                    queue.get(timeout=5)
