import pytest

from tests import factories


# TODO these tests belong somewhere else
@pytest.mark.django_db
@pytest.mark.parametrize('endpoint, factory, autocreated_count', [
    ('site_banners', factories.SiteBannerFactory, 0),
    ('sourceconfigs', factories.SourceConfigFactory, 0),
    ('sources', factories.SourceFactory, 1),
])
class TestPagination:

    def test_no_prev(self, client, endpoint, factory, autocreated_count):
        resp = client.get('/api/v2/{}/'.format(endpoint))
        assert resp.status_code == 200
        _json = resp.json()
        assert len(_json['data']) == autocreated_count
        _links = _json.get('links', {})
        assert _links.get('prev') is None
        assert _links.get('next') is None

    def test_one(self, client, endpoint, factory, autocreated_count):
        factory()

        resp = client.get('/api/v2/{}/'.format(endpoint))
        assert resp.status_code == 200
        _json = resp.json()
        assert len(_json['data']) == autocreated_count + 1
        _links = _json.get('links', {})
        assert _links.get('prev') is None
        assert _links.get('next') is None

    def test_full_page(self, client, endpoint, factory, autocreated_count):
        factory.create_batch(10 - autocreated_count)
        resp = client.get('/api/v2/{}/'.format(endpoint))
        assert resp.status_code == 200
        _json = resp.json()
        assert len(_json['data']) == 10
        _links = _json.get('links', {})
        assert _links.get('prev') is None
        assert _links.get('next') is None

    def test_next_page(self, client, endpoint, factory, autocreated_count):
        factory.create_batch(20 - autocreated_count)
        resp = client.get('/api/v2/{}/'.format(endpoint))
        assert resp.status_code == 200

        _json = resp.json()
        assert len(_json['data']) == 10
        _links = _json.get('links', {})
        assert _links.get('prev') is None
        assert _links.get('next') is not None
        assert 'page%5Bcursor%5D' in _links['next']

        resp2 = client.get(_links['next'])
        assert resp2.status_code == 200
        _json2 = resp2.json()
        assert _json2['links'].get('next') is None

        assert set(x['id'] for x in _json['data']) & set(x['id'] for x in _json2['data']) == set()

    def test_bad_cursor(self, client, endpoint, factory, autocreated_count):
        resp = client.get(f'/api/v2/{endpoint}/', {'page[cursor]': 1})
        assert resp.status_code == 404
        assert resp.json() == {'errors': [{
            'code': 'not_found',
            'status': '404',
            'detail': 'Invalid cursor',
            'source': {'pointer': '/data'},
        }]}
