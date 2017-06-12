import json
import pytest
from unittest import mock

from django.test import override_settings

from share.models import ChangeSet


@pytest.mark.django_db
class TestV1PushProxy:

    @pytest.fixture(autouse=True)
    def mock_disambiguate(self):
        with mock.patch('api.views.workflow.disambiguate') as mock_disambiguate:
            mock_disambiguate.delay().id = '123'
            yield mock_disambiguate

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
    def test_invalid_data(self, client, trusted_user, data):
        assert client.post(
            '/api/v1/share/data/',
            json.dumps(data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer ' + trusted_user.accesstoken_set.first().token
        ).status_code == 400

    @override_settings(CELERY_ALWAYS_EAGER=True)
    def test_valid_data(self, client, trusted_user):

        assert client.post(
            '/api/v1/share/data/',
            json.dumps(self.valid_data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer ' + trusted_user.accesstoken_set.first().token
        ).status_code == 202

        qs = ChangeSet.objects.filter(
            normalized_data__source=trusted_user.id
        )

        qs_accepted = ChangeSet.objects.filter(
            normalized_data__source=trusted_user.id,
            status=ChangeSet.STATUS.accepted
        )

        assert len(qs) == len(qs_accepted)

    def test_unauthorized(self, client):
        assert client.post(
            '/api/v1/share/data/',
            json.dumps(self.valid_data),
            content_type='application/json'
        ).status_code == 401

    def test_get(self, client):
        assert client.get('/api/v1/share/data/').status_code == 405

    def test_token_auth(self, client, trusted_user):
        assert client.post(
            '/api/v1/share/data/',
            json.dumps({}),
            content_type='application/json',
            HTTP_AUTHORIZATION='Token ' + trusted_user.accesstoken_set.first().token
        ).status_code == 400
