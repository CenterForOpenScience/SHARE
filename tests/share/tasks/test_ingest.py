import json

import pytest

from share.tasks import ingest
from tests import factories


@pytest.mark.django_db
class TestIngestJobConsumer:
    def test_no_output(self):
        raw = factories.RawDatumFactory(datum=json.dumps({
            '@graph': []
        }))
        job = factories.IngestJobFactory(raw=raw)

        assert not raw.no_output

        ingest(job_id=job.id)

        raw.refresh_from_db()

        assert raw.no_output
