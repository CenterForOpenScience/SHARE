import json
import pytest


@pytest.mark.django_db
class TestV1PushProxy:

    valid_data = {
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

    @pytest.fixture()
    def trusted_user(self):
        from share.models import ShareUser
        user = ShareUser(username='tester', is_trusted=True)
        user.save()
        return user

    def test_invalid_data(self, client, trusted_user):
        data = {
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

        assert client.post(
            '/api/v1/share/data/',
            json.dumps(data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer ' + trusted_user.accesstoken_set.first().token
        ).status_code == 400

    def test_valid_data(self, client, trusted_user):

        assert client.post(
            '/api/v1/share/data/',
            json.dumps(self.valid_data),
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer ' + trusted_user.accesstoken_set.first().token
        ).status_code == 202

    def test_unauthorized(self, client):
        assert client.post(
            '/api/v1/share/data/',
            json.dumps(self.valid_data),
            content_type='application/json'
        ).status_code == 401

    def test_get(self, client):
        assert client.get('/api/v1/share/data/').status_code == 405
