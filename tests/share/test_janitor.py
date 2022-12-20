import pytest

from share.janitor.tasks import rawdata_janitor
from share.models import IngestJob

from tests import factories


@pytest.mark.django_db
def test_empty():
    rawdata_janitor()

    assert IngestJob.objects.count() == 0


@pytest.mark.django_db
def test_ignores_no_output():
    factories.RawDatumFactory.create_batch(25, no_output=True)

    assert rawdata_janitor() == 0
    assert IngestJob.objects.count() == 0


@pytest.mark.usefixtures('nested_django_db')
class TestRawDataJanitor:
    @pytest.fixture(scope='class')
    def rds(self, class_scoped_django_db):
        return factories.RawDatumFactory.create_batch(55)

    def test_unprocessed_data(self, rds):
        assert rawdata_janitor() == 55
        assert IngestJob.objects.count() == 55
        assert all(rd.ingest_jobs.count() == 1 for rd in rds)

    def test_idempotent(self, rds):
        for rd in rds:
            factories.NormalizedDataFactory(raw=rd)

        assert rawdata_janitor() == 0
        assert rawdata_janitor() == 0

        assert IngestJob.objects.count() == 0

    def test_some_unprocessed_date(self, rds):
        for rd in rds[:25]:
            factories.NormalizedDataFactory(raw=rd)

        assert rawdata_janitor() == 30
        assert IngestJob.objects.count() == 30
