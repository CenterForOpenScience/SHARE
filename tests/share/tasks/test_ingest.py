import json
from unittest import mock

import pendulum
import pytest
from queue import Empty

from django.apps import apps
from django.conf import settings

from share.models import NormalizedData
from share.tasks import ingest
from share.util.graph import MutableGraph
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

    @pytest.mark.parametrize('legacy', [True, False])
    def test_legacy_pipeline(self, legacy, monkeypatch):
        mock_apply_changes = mock.Mock(return_value=[])
        monkeypatch.setattr('share.tasks.jobs.IngestJobConsumer._apply_changes', mock_apply_changes)
        monkeypatch.setattr('django.conf.settings.SHARE_LEGACY_PIPELINE', legacy)

        g = MutableGraph()
        g.add_node('_:id', 'creativework', title='This is a title')

        job = factories.IngestJobFactory(raw__datum=json.dumps({
            '@graph': g.to_jsonld(in_edges=False)
        }))

        ingest.apply(kwargs={'job_id': job.id}, throw=True)

        if legacy:
            assert NormalizedData.objects.count() == 1
            assert mock_apply_changes.call_count == 1
        else:
            assert NormalizedData.objects.count() == 0
            assert not mock_apply_changes.called

    def test_elastic_queue(self, celery_app):
        user = factories.ShareUserFactory(is_trusted=True)
        ingester = Ingester({
            '@graph': [{
                '@id': '_:1234',
                '@type': 'creativework',
                'title': 'All About Tamanduas',
            }]
        }).as_user(user).setup_ingest(claim_job=True)

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
        }).as_user(user).setup_ingest(claim_job=True)

        with celery_app.pool.acquire(block=True) as connection:
            index = settings.ELASTICSEARCH['ACTIVE_INDEXES'][0]
            queue_name = settings.ELASTICSEARCH['INDEXES'][index]['DEFAULT_QUEUE']
            with connection.SimpleQueue(queue_name, **settings.ELASTICSEARCH['QUEUE_SETTINGS']) as queue:
                queue.clear()

                celery_app.tasks['share.tasks.ingest'](job_id=ingester.job.id)

                with pytest.raises(Empty):
                    queue.get(timeout=5)
