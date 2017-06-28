import pytest
import json
from unittest import mock

from share import tasks

from tests import factories


@pytest.mark.django_db
class TestTransform:

    @pytest.fixture(autouse=True)
    def mock_requests(self, monkeypatch):
        mrequests = mock.Mock()
        monkeypatch.setattr('share.tasks.requests', mrequests)
        return mrequests

    def test_set_no_output(self):
        raw = factories.RawDatumFactory(datum=json.dumps({
            '@graph': []
        }))

        tasks.transform(raw.id)

        raw.refresh_from_db()

        assert raw.no_output is True

    def test_does_not_set_no_output(self):
        raw = factories.RawDatumFactory(datum=json.dumps({
            '@graph': []
        }))

        factories.NormalizedDataFactory(raw=raw)

        tasks.transform(raw.id)

        raw.refresh_from_db()

        assert raw.no_output is None
