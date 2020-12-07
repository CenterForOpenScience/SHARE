import json

import pendulum
import pytest

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
