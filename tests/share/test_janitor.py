import pytest
from unittest import mock

from share.janitor.tasks import rawdata_janitor

from tests import factories


@pytest.mark.django_db
class TestRawDataJanitor:

    @pytest.fixture(autouse=True)
    def mock_transform(self, monkeypatch):
        mock_transform = mock.Mock()
        monkeypatch.setattr('share.tasks.transform.apply', mock_transform)
        return mock_transform

    def test_empty(self, mock_transform):
        rawdata_janitor()

        assert mock_transform.called is False

    def test_unprocessed_data(self, mock_transform):
        rds = factories.RawDatumFactory.create_batch(55)
        assert rawdata_janitor() == 55
        assert mock_transform.call_args_list == [
            mock.call((rd.id,), throw=True, retries=4)
            for rd in sorted(rds, key=lambda r: r.id)
        ]

    def test_idempotent(self, mock_transform):
        rds = factories.RawDatumFactory.create_batch(55)

        for rd in rds:
            factories.NormalizedDataFactory(raw=rd)

        assert rawdata_janitor() == 0
        assert rawdata_janitor() == 0

        assert mock_transform.call_args_list == []

    def test_some_unprocessed_date(self, mock_transform):
        rds = factories.RawDatumFactory.create_batch(55)
        for rd in rds[:25]:
            factories.NormalizedDataFactory(raw=rd)

        assert rawdata_janitor() == 30

        assert mock_transform.call_args_list == [
            mock.call((rd.id,), throw=True, retries=4)
            for rd in sorted(rds[25:], key=lambda r: r.id)
        ]
