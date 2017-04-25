from unittest import mock


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

    def test_limitted_post(self, client):
        assert client.post('/api/v2/search/type').status_code == 403
        assert client.post('/api/v2/search/type/').status_code == 403
        assert client.post('/api/v2/search/type/id').status_code == 403
        assert client.post('/api/v2/search/type/id/').status_code == 403
        assert client.post('/api/v2/search/type/id/some/thing/else').status_code == 403
        assert client.post('/api/v2/search/type/id/some/thing/else/').status_code == 403
        assert client.post('/api/v2/search/type/id/_search').status_code == 403
        assert client.post('/api/v2/search/type/id/_search/').status_code == 403
        assert client.post('/api/v2/search/type/id/some/thing/else/_search').status_code == 403
        assert client.post('/api/v2/search/type/id/some/thing/else/_search/').status_code == 403
        assert client.post('/api/v2/search/type/id/some/thing/else/_count').status_code == 403
        assert client.post('/api/v2/search/type/id/some/thing/else/_count/').status_code == 403

    def test_scroll_forbidden(self, client):
        assert client.post('/api/v2/search/_search/scroll').status_code == 403
        assert client.post('/api/v2/search/_search/?scroll=1m').status_code == 403
        assert client.get('/api/v2/search/_search/scroll').status_code == 403
        assert client.get('/api/v2/search/_search/?scroll=1m').status_code == 403

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
        with mock.patch('api.views.elasticsearch.requests.post') as post:
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
        with mock.patch('api.views.elasticsearch.requests.post') as post:
            post.return_value = mock.Mock(status_code=405, json=lambda: {})
            for url in urls:
                assert client.post(url, '{}', content_type='application/json').status_code == 405

    def test_get_search(self, client):
        urls = (
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
        )
        with mock.patch('api.views.elasticsearch.requests.get') as get:
            get.return_value = mock.Mock(status_code=200, json=lambda: {})
            for url in urls:
                assert client.get(url).status_code == 200

    def test_cannot_get(self, client):
        urls = (
            '/api/v2/search/_suggest',
            '/api/v2/search/_suggest/',
            '/api/v2/search/type/_suggest',
            '/api/v2/search/type/_suggest/',
        )
        with mock.patch('api.views.elasticsearch.requests.get') as get:
            get.return_value = mock.Mock(status_code=405, json=lambda: {})
            for url in urls:
                assert client.get(url).status_code == 405
