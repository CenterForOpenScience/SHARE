import pytest
import json


@pytest.fixture
def post_body_share_user():
    return json.dumps({
        'data': {
            'type': 'ShareUser',
            'attributes': {
                'username': 'TestUser'
            }
        }
    })


@pytest.mark.django_db
class TestSourcesGet:
    endpoint = '/api/v2/user/'

    def test_logged_in(self, client, share_user):
        resp = client.get(self.endpoint, HTTP_AUTHORIZATION=share_user.authorization())
        assert resp.status_code == 200
        assert resp.json()['meta']['pagination']['count'] == 1

    def test_not_logged_in(self, client):
        resp = client.get(self.endpoint)
        assert resp.status_code == 200
        assert resp.json()['meta']['pagination']['count'] == 0


@pytest.mark.django_db
class TestSourcesPost:
    endpoint = '/api/v2/user/'

    def test_unauthorized_post(self, client, post_body_share_user):
        assert client.post(
            self.endpoint,
            post_body_share_user,
            content_type='application/vnd.api+json'
        ).status_code == 401

    def test_authorized_post(self, client, share_user, post_body_share_user):
        assert client.post(
            self.endpoint,
            post_body_share_user,
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=share_user.authorization(),
        ).status_code == 405
