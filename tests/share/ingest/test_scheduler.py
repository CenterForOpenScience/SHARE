import pytest
from unittest import mock
import pendulum

from share.ingest.scheduler import IngestScheduler
from share.models.jobs import IngestJob
from share.models.ingest import SourceUniqueIdentifier

from tests import factories


@pytest.mark.usefixtures('nested_django_db')
class TestIngestScheduler:

    @pytest.fixture
    def mock_consume(self):
        with mock.patch('share.tasks.jobs.IngestJobConsumer.consume') as mock_consume:
            yield mock_consume

    @pytest.fixture
    def mock_ingest(self):
        with mock.patch('share.ingest.scheduler.ingest') as mock_ingest:
            yield mock_ingest

    @pytest.fixture(scope='class')
    def suid(self, class_scoped_django_db):
        return factories.SourceUniqueIdentifierFactory()

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
    def test_schedule(self, suid, raw_ages, selected_raw, claim, prior_status, superfluous, expected_status):
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

    def test_reingest(self, suid, mock_consume):
        raw = factories.RawDatumFactory(suid=suid)
        job = IngestScheduler().reingest(raw.suid)
        assert job.claimed
        mock_consume.assert_called_once_with(job_id=job.id, exhaust=False, superfluous=True)

    def test_reingest_async(self, suid, mock_ingest):
        raw = factories.RawDatumFactory(suid=suid)
        job = IngestScheduler().reingest_async(raw.suid)
        assert job.claimed
        mock_ingest.delay.assert_called_once_with(job_id=job.id, exhaust=False, superfluous=True)

    @pytest.mark.parametrize('claim', [True, False])
    @pytest.mark.parametrize('superfluous', [True, False])
    def test_bulk_schedule(self, claim, superfluous):
        suid_specs = [
            # raw_ages, expected_raw, job_status
            ([0, 1, 2], 0, 'created'),
            ([5, 4, 2, 3], 2, 'failed'),
            ([2, 1], 1, 'succeeded'),
            ([4, 2], 1, None),
        ]
        suids = set()
        expected_jobs = set()
        for raw_ages, selected_raw, job_status in suid_specs:
            suid = factories.SourceUniqueIdentifierFactory()
            raws = [
                factories.RawDatumFactory(
                    suid=suid,
                    datestamp=pendulum.now().subtract(days=days_ago)
                )
                for days_ago in raw_ages
            ]
            if job_status:
                job = factories.IngestJobFactory(
                    raw=raws[selected_raw],
                    status=getattr(IngestJob.STATUS, job_status)
                )
                expected_jobs.add(job)
            suids.add(suid)

        actual_jobs = IngestScheduler().bulk_schedule(
            SourceUniqueIdentifier.objects.filter(id__in=[suid.id for suid in suids]),
            claim=claim,
            superfluous=superfluous,
        )

        assert len(actual_jobs) == len(suids)
        assert expected_jobs.issubset(actual_jobs)
        for job in actual_jobs:
            assert bool(job.claimed) == claim
            if superfluous:
                assert job.status == IngestJob.STATUS.created

    def test_bulk_reingest(self, mock_ingest):
        with mock.patch('share.ingest.scheduler.IngestScheduler.bulk_schedule') as mock_bulk_schedule:
            jobs = [
                factories.IngestJobFactory()
                for _ in range(10)
            ]
            mock_bulk_schedule.return_value = jobs
            actual_jobs = IngestScheduler().bulk_reingest(mock.sentinel.suid_qs)

            mock_bulk_schedule.assert_called_once_with(
                mock.sentinel.suid_qs,
                superfluous=True,
                claim=True
            )

            assert actual_jobs is jobs
            assert mock_ingest.delay.call_args_list == [
                ({
                    'job_id': j.id,
                    'exhaust': False,
                    'superfluous': True,
                },)
                for j in actual_jobs
            ]
