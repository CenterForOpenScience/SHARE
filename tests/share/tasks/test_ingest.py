import json

import pendulum
import pytest
from queue import Empty

from django.apps import apps
from django.conf import settings

from share.tasks import ingest
from share.ingest.ingester import Ingester
from tests import factories


@pytest.mark.django_db
class TestIngestJobConsumer:
    def test_pointless(self):
        job = factories.IngestJobFactory(raw__datestamp=pendulum.now().subtract(hours=2))
        factories.IngestJobFactory(suid=job.suid, raw__datestamp=pendulum.now().subtract(hours=1))

        ingest(job_id=job.id)

        job.refresh_from_db()
        assert job.status == job.STATUS.skipped
        assert job.error_context == job.SkipReasons.pointless.value

    def test_no_output(self):
        raw = factories.RawDatumFactory(datum=json.dumps({
            '@graph': []
        }))
        job = factories.IngestJobFactory(raw=raw)

        assert not raw.no_output

        ingest(job_id=job.id)

        raw.refresh_from_db()

        assert raw.no_output

    def test_elastic_queue(self, celery_app):
        user = factories.ShareUserFactory(is_trusted=True)
        ingester = Ingester({
            '@graph': [{
                '@id': '_:1234',
                '@type': 'creativework',
                'title': 'All About Tamanduas',
            }]
        }).as_user(user).ingest_async(start_task=False)

        with celery_app.pool.acquire(block=True) as connection:
            index = settings.ELASTICSEARCH['ACTIVE_INDEXES'][0]
            queue_name = settings.ELASTICSEARCH['INDEXES'][index]['DEFAULT_QUEUE']
            with connection.SimpleQueue(queue_name, **settings.ELASTICSEARCH['QUEUE_SETTINGS']) as queue:
                queue.clear()

                celery_app.tasks['share.tasks.ingest'](job_id=ingester.job.id)

                message = queue.get(timeout=5)
                assert len(apps.get_model('share', message.payload['model']).objects.filter(id__in=message.payload['ids'])) == len(message.payload['ids'])

    def test_elastic_queue_only_works(self, celery_app):
        user = factories.ShareUserFactory(is_trusted=True)
        ingester = Ingester({
            '@graph': [{
                '@id': '_:1234',
                '@type': 'person',
                'given_name': 'Jane',
                'family_name': 'Doe',
            }]
        }).as_user(user).ingest_async(start_task=False)

        with celery_app.pool.acquire(block=True) as connection:
            index = settings.ELASTICSEARCH['ACTIVE_INDEXES'][0]
            queue_name = settings.ELASTICSEARCH['INDEXES'][index]['DEFAULT_QUEUE']
            with connection.SimpleQueue(queue_name, **settings.ELASTICSEARCH['QUEUE_SETTINGS']) as queue:
                queue.clear()

                celery_app.tasks['share.tasks.ingest'](job_id=ingester.job.id)

                with pytest.raises(Empty):
                    queue.get(timeout=5)
