import pytest

from tests import factories


# TODO these tests belong somewhere else
@pytest.mark.django_db
@pytest.mark.parametrize('endpoint, factory', [
    ('normalizeddata', factories.NormalizedDataFactory),
    ('rawdata', factories.RawDatumFactory),
])
class TestPagination:

    def test_no_prev(self, client, endpoint, factory):
        resp = client.get('/api/v2/{}/'.format(endpoint))
        assert resp.status_code == 200
        assert resp.json()['data'] == []
        assert resp.json()['links']['prev'] is None
        assert resp.json()['links']['next'] is None

    def test_one(self, client, endpoint, factory):
        factory()

        resp = client.get('/api/v2/{}/'.format(endpoint))
        assert resp.status_code == 200
        assert len(resp.json()['data']) == 1
        assert resp.json()['links']['prev'] is None
        assert resp.json()['links']['next'] is None

    def test_full_page(self, client, endpoint, factory):
        for _ in range(10):
            factory()

        resp = client.get('/api/v2/{}/'.format(endpoint))
        assert resp.status_code == 200

        assert len(resp.json()['data']) == 10
        assert resp.json()['links']['prev'] is None
        assert resp.json()['links']['next'] is None

    def test_next_page(self, client, endpoint, factory):
        for _ in range(20):
            factory()

        resp = client.get('/api/v2/{}/'.format(endpoint))
        assert resp.status_code == 200

        assert len(resp.json()['data']) == 10
        assert resp.json()['links']['prev'] is None
        assert resp.json()['links']['next'] is not None
        assert 'page%5Bcursor%5D' in resp.json()['links']['next']

        resp2 = client.get(resp.json()['links']['next'])
        assert resp2.status_code == 200
        assert resp2.json()['links']['next'] is None

        assert set(x['id'] for x in resp.json()['data']) & set(x['id'] for x in resp2.json()['data']) == set()

    def test_bad_cursor(self, client, endpoint, factory):
        resp = client.get(f'/api/v2/{endpoint}/', {'page[cursor]': 1})
        assert resp.status_code == 404
        assert resp.json() == {'errors': [{
            'code': 'not_found',
            'status': '404',
            'detail': 'Invalid cursor',
            'source': {'pointer': '/data'},
        }]}
