import pytest
from unittest import mock
import pendulum

from share.ingest.scheduler import IngestScheduler
from share.models.jobs import IngestJob

from tests import factories


@pytest.mark.django_db
class TestIngestScheduler:

    @pytest.fixture
    def mock_schedule(self):
        with mock.patch('share.ingest.IngestScheduler.schedule') as mock_schedule:
            mock_schedule.return_value = factories.IngestJobFactory()
            yield mock_schedule

    @pytest.fixture
    def mock_consume(self):
        with mock.patch('share.tasks.jobs.IngestJobConsumer.consume') as mock_consume:
            yield mock_consume

    @pytest.fixture
    def mock_ingest(self):
        with mock.patch('share.ingest.scheduler.ingest') as mock_ingest:
            yield mock_ingest

    @pytest.fixture
    def mock_bulk_job(self):
        with mock.patch('share.models.jobs.AbstractJobManager.bulk_get_or_create') as mock_bulk_job:
            yield mock_bulk_job

    @pytest.mark.parametrize('raw_ages, selected_raw', [
        ([0, 1, 2], 0),
        ([5, 4, 2, 3], 2),
        ([2, 1], 1),
    ])
    @pytest.mark.parametrize('claim', [True, False])
    @pytest.mark.parametrize('prior_status, superfluous, expected_status', [
        (None, True, 'created'),
        (None, False, 'created'),
        ('created', True, 'created'),
        ('created', False, 'created'),
        ('started', True, 'started'),
        ('started', False, 'started'),
        ('failed', True, 'created'),
        ('failed', False, 'failed'),
        ('succeeded', True, 'created'),
        ('succeeded', False, 'succeeded'),
    ])
    def test_schedule(self, raw_ages, selected_raw, claim, prior_status, superfluous, expected_status):
        suid = factories.SourceUniqueIdentifierFactory()
        raws = [
            factories.RawDatumFactory(
                suid=suid,
                datestamp=pendulum.now().subtract(days=days_ago)
            )
            for days_ago in raw_ages
        ]
        expected_raw = raws[selected_raw]

        expected_job = None
        if prior_status:
            expected_job = factories.IngestJobFactory(
                raw=expected_raw,
                status=getattr(IngestJob.STATUS, prior_status)
            )

        job = IngestScheduler().schedule(suid, claim=claim, superfluous=superfluous)

        if expected_job:
            assert job.id == expected_job.id
        assert job.suid_id == suid.id
        assert job.raw_id == expected_raw.id
        assert job.status == getattr(IngestJob.STATUS, expected_status)
        assert job.claimed == claim

    def test_reingest(self, mock_consume):
        raw = factories.RawDatumFactory()
        job = IngestScheduler().reingest(raw.suid)
        assert job.claimed
        mock_consume.assert_called_once_with(job_id=job.id, exhaust=False, superfluous=True)

    def test_reingest_async(self, mock_ingest):
        raw = factories.RawDatumFactory()
        job = IngestScheduler().reingest_async(raw.suid)
        assert job.claimed
        mock_ingest.delay.assert_called_once_with(job_id=job.id, exhaust=False, superfluous=True)

    def test_bulk_reingest(self):
        pass
