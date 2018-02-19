import json
import pytest
from unittest import mock


@pytest.mark.django_db
class TestV1PushProxy:

    @pytest.fixture
    def mock_ingest(self):
        with mock.patch('share.ingest.ingest') as mock_ingest:
            mock_ingest.delay.return_value.id = '123'
            yield mock_ingest

    valid_data = {
        "jsonData": {
            "providerUpdatedDateTime": "2016-08-25T11:37:40Z",
            "uris": {
                "canonicalUri": "https://provider.domain/files/7d2792031",
                "providerUris": ["https://provider.domain/files/7d2792031"]
            },
            "contributors": [
                {"name": "Person1", "email": "one@provider.domain"},
                {"name": "Person2", "email": "two@provider.domain"},
                {"name": "Person3", "email": "three@provider.domain"},
                {"name": "Person4", "email": "four@provider.domain"}
            ],
            "title": "Title"
        }
    }

    @pytest.mark.parametrize('data', [{
        "jsonData": {
            "providerUpdatedDateTime": "2016-08-25T11:37:40Z",
            "uris": {
                "providerUris": ["https://provider.domain/files/7d2792031"]
            },
            "contributors": [
                {"name": "Person1", "email": "one@provider.domain"},
                {"name": "Person2", "email": "two@provider.domain"},
                {"name": "Person3", "email": "three@provider.domain"},
                {"name": "Person4", "email": "four@provider.domain"}
            ],
            "title": "Title"
        }
    }, {
    }, {
        "providerUpdatedDateTime": "2016-08-25T11:37:40Z",
        "uris": {
            "providerUris": ["https://provider.domain/files/7d2792031"]
        },
        "contributors": [
            {"name": "Person1", "email": "one@provider.domain"},
            {"name": "Person2", "email": "two@provider.domain"},
            {"name": "Person3", "email": "three@provider.domain"},
            {"name": "Person4", "email": "four@provider.domain"}
        ],
        "title": "Title"
    }
    ])
    def test_invalid_data(self, client, trusted_user, data, mock_ingest):
        assert client.post(
            '/api/v1/share/data/',
            json.dumps(data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer ' + trusted_user.accesstoken_set.first().token
        ).status_code == 400
        assert not mock_ingest.delay.called

    def test_valid_data(self, client, trusted_user, mock_ingest):
        assert client.post(
            '/api/v1/share/data/',
            json.dumps(self.valid_data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer ' + trusted_user.accesstoken_set.first().token
        ).status_code == 202

        assert mock_ingest.delay.called

    def test_unauthorized(self, client, mock_ingest):
        assert client.post(
            '/api/v1/share/data/',
            json.dumps(self.valid_data),
            content_type='application/json'
        ).status_code == 401
        assert not mock_ingest.delay.called

    def test_get(self, client, mock_ingest):
        assert client.get('/api/v1/share/data/').status_code == 405
        assert not mock_ingest.delay.called

    def test_token_auth(self, client, trusted_user, mock_ingest):
        assert client.post(
            '/api/v1/share/data/',
            json.dumps({}),
            content_type='application/json',
            HTTP_AUTHORIZATION='Token ' + trusted_user.accesstoken_set.first().token
        ).status_code == 400
        assert not mock_ingest.delay.called
