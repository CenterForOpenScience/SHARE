import json
from unittest import mock

import pendulum
import pytest

from share.models import NormalizedData
from share.regulate.graph import MutableGraph
from share.tasks import ingest
from tests import factories


@pytest.mark.django_db
class TestIngestJobConsumer:
    def test_pointless(self):
        job = factories.IngestJobFactory(raw__datestamp=pendulum.now().subtract(hours=2))
        factories.IngestJobFactory(suid=job.suid, raw__datestamp=pendulum.now().subtract(hours=1))

        ingest(job_id=job.id)

        job.refresh_from_db()
        assert job.status == job.STATUS.skipped
        assert job.context == job.SkipReasons.pointless.value

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
        mock_disambiguate = mock.Mock()
        monkeypatch.setattr('share.tasks.disambiguate', mock_disambiguate)
        monkeypatch.setattr('django.conf.settings.SHARE_LEGACY_PIPELINE', legacy)

        g = MutableGraph()
        g.add_node('_:id', 'creativework', title='This is a title')

        job = factories.IngestJobFactory(raw__datum=json.dumps({
            '@graph': g.to_jsonld(in_edges=False)
        }))

        ingest.apply(kwargs={'job_id': job.id})

        if legacy:
            assert NormalizedData.objects.count() == 1
            assert mock_disambiguate.apply_async.call_count == 1
        else:
            assert NormalizedData.objects.count() == 0
            assert not mock_disambiguate.apply_async.called
