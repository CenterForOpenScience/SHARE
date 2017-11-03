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


@pytest.fixture(params=[
    '/api/v2/user/',
    '/api/v2/users/',
])
def endpoint(request):
    return request.param


@pytest.mark.django_db
class TestSourcesGet:

    def test_logged_in(self, endpoint, client, share_user):
        resp = client.get(endpoint, HTTP_AUTHORIZATION=share_user.authorization())
        assert resp.status_code == 200
        assert resp.json()['meta']['pagination']['count'] == 1

    def test_not_logged_in(self, endpoint, client):
        resp = client.get(endpoint)
        assert resp.status_code == 200
        assert resp.json()['meta']['pagination']['count'] == 0


@pytest.mark.django_db
class TestSourcesPost:

    def test_unauthorized_post(self, endpoint, client, post_body_share_user):
        assert client.post(
            endpoint,
            post_body_share_user,
            content_type='application/vnd.api+json'
        ).status_code == 401

    def test_authorized_post(self, endpoint, client, share_user, post_body_share_user):
        assert client.post(
            endpoint,
            post_body_share_user,
            content_type='application/vnd.api+json',
            HTTP_AUTHORIZATION=share_user.authorization(),
        ).status_code == 405
