from furl import furl
from unittest import mock
import pytest


class TestElasticSearchProxy:

    def test_cannot_put(self, client):
        assert client.put('/api/v2/search/').status_code == 405
        assert client.put('/api/v2/search/thing').status_code == 405
        assert client.put('/api/v2/search/_count').status_code == 405
        assert client.put('/api/v2/search/_search').status_code == 405
        assert client.put('/api/v2/search/type/index').status_code == 405
        assert client.put('/api/v2/search/type/index/_thing').status_code == 405

    def test_cannot_delete(self, client):
        assert client.delete('/api/v2/search/').status_code == 405
        assert client.delete('/api/v2/search/thing').status_code == 405
        assert client.delete('/api/v2/search/_count').status_code == 405
        assert client.delete('/api/v2/search/_search').status_code == 405
        assert client.delete('/api/v2/search/type/index').status_code == 405
        assert client.delete('/api/v2/search/type/index/_thing').status_code == 405

    def test_cannot_access_bulk(self, client):
        assert client.delete('/api/v2/search/_bulk').status_code == 405
        assert client.delete('/api/v2/search/_bulk?test').status_code == 405
        assert client.delete('/api/v2/search/type/_bulk?foo').status_code == 405
        assert client.delete('/api/v2/search/type/index/_bulk').status_code == 405

    def test_scroll_forbidden(self, client):
        assert client.post('/api/v2/search/_search/scroll').status_code == 403
        assert client.post('/api/v2/search/_search/?scroll=1m').status_code == 403
        assert client.get('/api/v2/search/_search/scroll').status_code == 403
        assert client.get('/api/v2/search/_search/?scroll=1m').status_code == 403

    @pytest.mark.parametrize('url', [
        '/api/v2/search/type',
        '/api/v2/search/type/',
        '/api/v2/search/type/id',
        '/api/v2/search/type/id/',
        '/api/v2/search/type/id/some/thing/else',
        '/api/v2/search/type/id/some/thing/else/',
        '/api/v2/search/type/id/_search',
        '/api/v2/search/type/id/_search/',
        '/api/v2/search/type/id/some/thing/else/_search',
        '/api/v2/search/type/id/some/thing/else/_search/',
        '/api/v2/search/type/id/some/thing/else/_count',
        '/api/v2/search/type/id/some/thing/else/_count/',
        '/api/v2/search/_coun',
        '/api/v2/search/__count',
        '/api/v2/search/_counttttttttttt',
        '/api/v2/search/_sear',
        '/api/v2/search/__search',
        '/api/v2/search/_searchh',
        '/api/v2/search/_sugges',
        '/api/v2/search/__suggest',
        '/api/v2/search/_ssuggest',
    ])
    def test_limitted_post(self, url, client):
        with mock.patch('api.search.views.requests.post') as post:
            post.return_value = mock.Mock(status_code=500, json=lambda: {})
            assert client.post(url, '{}', content_type='application/json').status_code in (403, 405)

    @pytest.mark.parametrize('url', [
        '/api/v2/search/type',
        '/api/v2/search/type/',
        '/api/v2/search/type/id/some/thing/else',
        '/api/v2/search/type/id/some/thing/else/',
        '/api/v2/search/type/id/_search',
        '/api/v2/search/type/id/_search/',
        '/api/v2/search/type/id/some/thing/else/_search',
        '/api/v2/search/type/id/some/thing/else/_search/',
        '/api/v2/search/type/id/some/thing/else/_count',
        '/api/v2/search/type/id/some/thing/else/_count/',
        '/api/v2/search/_coun',
        '/api/v2/search/__count',
        '/api/v2/search/_counttttttttttt',
        '/api/v2/search/_sear',
        '/api/v2/search/__search',
        '/api/v2/search/_searchh',
        '/api/v2/search/_mapping',
        '/api/v2/search/__mappings',
        '/api/v2/search/_mappingss',
    ])
    def test_limitted_get(self, url, client):
        with mock.patch('api.search.views.requests.get') as get:
            get.return_value = mock.Mock(status_code=500, json=lambda: {})
            assert client.post(url).status_code == 403

    def test_post_search(self, client):
        urls = (
            '/api/v2/search/_search',
            '/api/v2/search/_search/',
            '/api/v2/search/_suggest',
            '/api/v2/search/_suggest/',
            '/api/v2/search/type/_count',
            '/api/v2/search/type/_count/',
            '/api/v2/search/type/_search',
            '/api/v2/search/type/_search/',
            '/api/v2/search/type/_suggest',
            '/api/v2/search/type/_suggest/',
        )
        with mock.patch('api.search.views.requests.post') as post:
            post.return_value = mock.Mock(status_code=200, json=lambda: {})
            for url in urls:
                assert client.post(url, '{}', content_type='application/json').status_code == 200

    def test_cannot_post(self, client):
        urls = (
            '/api/v2/search/_mappings/',
            '/api/v2/search/_mappings',
            '/api/v2/search/_mappings/creativeworks',
            '/api/v2/search/_mappings/creativeworks/',
        )
        with mock.patch('api.search.views.requests.post') as post:
            post.return_value = mock.Mock(status_code=500, json=lambda: {})
            for url in urls:
                assert client.post(url, '{}', content_type='application/json').status_code == 405

    @pytest.mark.parametrize('url', [
        '/api/v2/search/_search',
        '/api/v2/search/_search/',
        '/api/v2/search/type/_count',
        '/api/v2/search/type/_count/',
        '/api/v2/search/type/_search',
        '/api/v2/search/type/_search/',
        '/api/v2/search/_mappings/',
        '/api/v2/search/_mappings',
        '/api/v2/search/_mappings/creativeworks',
        '/api/v2/search/_mappings/creativeworks/',
        '/api/v2/search/creativeworks/some-id',
        '/api/v2/search/creativeworks/some-id/',
        '/api/v2/search/agent/some-id/',
        '/api/v2/search/agent/some_id/',
    ])
    def test_get_search(self, url, client):
        with mock.patch('api.search.views.requests.get') as get:
            get.return_value = mock.Mock(status_code=200, json=lambda: {})
            assert client.get(url).status_code == 200

    def test_cannot_get(self, client):
        urls = (
            '/api/v2/search/_suggest',
            '/api/v2/search/_suggest/',
            '/api/v2/search/type/_suggest',
            '/api/v2/search/type/_suggest/',
        )
        with mock.patch('api.search.views.requests.get') as get:
            get.return_value = mock.Mock(status_code=500, json=lambda: {})
            for url in urls:
                assert client.get(url).status_code == 405

    def test_elastic_proxy(self, client, elastic):
        with mock.patch('api.search.views.requests.get') as get:
            get.return_value = mock.Mock(status_code=200, json=lambda: {})
            client.get('/api/v2/search/_search')
            elastic_url = furl('{}{}/{}'.format(elastic.es_url, elastic.es_index, '_search'))
            get.assert_called_with(elastic_url)
