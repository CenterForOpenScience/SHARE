class TestElasticSearchProxy:

    def test_cannot_put(self, client):
        assert client.put('/api/search/').status_code == 405
        assert client.put('/api/search/thing').status_code == 405
        assert client.put('/api/search/_count').status_code == 405
        assert client.put('/api/search/_search').status_code == 405
        assert client.put('/api/search/type/index').status_code == 405
        assert client.put('/api/search/type/index/_thing').status_code == 405

    def test_cannot_delete(self, client):
        assert client.delete('/api/search/').status_code == 405
        assert client.delete('/api/search/thing').status_code == 405
        assert client.delete('/api/search/_count').status_code == 405
        assert client.delete('/api/search/_search').status_code == 405
        assert client.delete('/api/search/type/index').status_code == 405
        assert client.delete('/api/search/type/index/_thing').status_code == 405

    def test_cannot_access_bulk(self, client):
        assert client.delete('/api/search/_bulk').status_code == 404
        assert client.delete('/api/search/_bulk?test').status_code == 404
        assert client.delete('/api/search/type/_bulk?foo').status_code == 404
        assert client.delete('/api/search/type/index/_bulk').status_code == 404
