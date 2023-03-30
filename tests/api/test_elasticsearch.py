from unittest import mock

from django.http import QueryDict
from django.test.client import Client


class TestElasticSearchProxy:
    def test_invalid_paths(self):
        client = Client()
        invalid_paths = (
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
            '/api/v2/search/_mappings/',
            '/api/v2/search/_mappings',
            '/api/v2/search/_mappings/creativeworks',
            '/api/v2/search/_mappings/creativeworks/',
            '/api/v2/search/creativeworks/_search/scroll',
            '/api/v2/search/_search/?scroll=1m',
        )
        for invalid_path in invalid_paths:
            assert client.get(invalid_path).status_code == 404
            assert client.put(invalid_path).status_code == 404
            assert client.post(invalid_path).status_code == 404
            assert client.delete(invalid_path).status_code == 404

    def test_scroll_forbidden(self):
        client = Client()
        assert client.post('/api/v2/search/creativeworks/_search?scroll=1m').status_code == 403
        assert client.post('/api/v2/search/creativeworks/_search/?q=foo&scroll=1m').status_code == 403

    def test_search(self):
        client = Client()
        urls = (
            '/api/v2/search/creativeworks/_search?q=foo',
            '/api/v2/search/creativeworks/_search/?q=foo',
        )
        with mock.patch('api.search.views.IndexStrategy') as mock_IndexStrategy:
            mock_handle_query = (
                mock_IndexStrategy
                .get_for_searching
                .return_value
                .pls_handle_query__sharev2_backcompat
            )
            mock_handle_query.return_value = {'clop': 'clip'}
            for url in urls:
                # POST:
                mock_handle_query.reset_mock()
                post_resp = client.post(url, '{"blib":"blob"}', content_type='application/json')
                assert post_resp.status_code == 200
                assert post_resp.json() == {'clop': 'clip'}
                mock_handle_query.assert_called_once_with(
                    request_body={'blib': 'blob'},
                    request_queryparams=QueryDict('q=foo'),
                )
                # GET:
                mock_handle_query.reset_mock()
                get_resp = client.get(url)
                assert get_resp.status_code == 200
                assert get_resp.json() == {'clop': 'clip'}
                mock_handle_query.assert_called_once_with(
                    request_body={},
                    request_queryparams=QueryDict('q=foo'),
                )
