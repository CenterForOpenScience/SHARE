from unittest import mock
import json
import pytest
import requests


class Response:
    def __init__(self, status_code=200, json=None, keys=None):
        self.status_code = status_code
        self._json = json or {}
        self._keys = keys

    def json(self):
        return self._json

    def __eq__(self, other):
        assert other.status_code == self.status_code

        if self._keys:
            assert set(other.json().keys()) == self._keys
        else:
            assert other.json() == self.json()

        return True


class TestPostNormalizedData:

    POST_CASES = [{
        'authorized': False,
        'out': Response(401, json={'errors': [{
            'detail': 'Authentication credentials were not provided.',
            'source': {'pointer': '/data'},
            'status': '401'
        }]}),
        'in': requests.Request('POST', headers={'Content-Type': 'application/vnd.api+json'}, json={'data': 'bar'})
    }, {
        'authorized': False,
        'out': Response(401, json={'errors': [{
            'detail': 'Authentication credentials were not provided.',
            'source': {'pointer': '/data'},
            'status': '401'
        }]}),
        'in': requests.Request('POST', headers={'Content-Type': 'application/vnd.api+json'}, json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    '@graph': [{'@type': 'person', 'given_name': 'Jim'}]
                }
            }
        })
    }, {
        'authorized': False,
        'out': Response(401, json={'errors': [{
            'detail': 'Authentication credentials were not provided.',
            'source': {'pointer': '/data'},
            'status': '401'
        }]}),
        'in': requests.Request('POST', headers={'Content-Type': 'application/vnd.api+json', 'Authorization': 'Foo'}, json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    '@graph': [{'@type': 'person', 'given_name': 'Jim'}]
                }
            }
        })
    }, {
        'out': Response(400, json={'errors': [{
            'detail': 'Received document does not contain primary data',
            'source': {'pointer': '/data'},
            'status': '400'
        }]}),
        'in': requests.Request('POST', headers={'Content-Type': 'application/vnd.api+json'}, json={})
    }, {
        'out': Response(400, json={'errors': [{
            'detail': 'JSON parse error - Expecting value: line 1 column 1 (char 0)',
            'source': {'pointer': '/data'},
            'status': '400'
        }]}),
        'in': requests.Request('POST', headers={'Content-Type': 'application/vnd.api+json'}, data='<html!>')
    }, {
        'out': Response(400, json={
            'errors': [
                {
                    'detail': '@graph may not be empty',
                    'source': {'pointer': '/data/attributes/data'},
                    'status': '400'
                }
            ]
        }),
        'in': requests.Request('POST', headers={'Content-Type': 'application/vnd.api+json'}, json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    'data': {'@graph': []}
                }
            }
        })
    }, {
        'out': Response(202, keys={'data'}),
        'in': requests.Request('POST', headers={'Content-Type': 'application/vnd.api+json'}, json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    'data': {
                        '@graph': [{
                            '@id': '_:100',
                            '@type': 'Person',
                            'given_name': 'Jim',
                        }]
                    }
                }
            }
        })
    }, {
        'out': Response(400, json={
            'errors': [
                {
                    'detail': "'@id' is a required property at /@graph/0",
                    'source': {'pointer': '/data/attributes/data'},
                    'status': '400'
                }
            ]
        }),
        'in': requests.Request('POST', headers={'Content-Type': 'application/vnd.api+json'}, json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    'data': {
                        '@graph': [{
                            '@type': 'Person',
                            'given_name': 'Jim',
                        }]
                    }
                }
            }
        })
    }]

    @pytest.mark.django_db
    @pytest.mark.parametrize('_request, response, authorized', [(case['in'], case['out'], case.get('authorized', True)) for case in POST_CASES])
    def test_post_data(self, trusted_user, client, _request, response, authorized):
        args, kwargs = (), {'content_type': 'application/vnd.api+json'}

        if _request.data:
            kwargs['data'] = _request.data
        elif _request.json is not None:
            kwargs['data'] = json.dumps(_request.json)

        if authorized:
            kwargs['HTTP_AUTHORIZATION'] = 'Bearer {}'.format(trusted_user.accesstoken_set.first())

        with mock.patch('api.views.workflow.disambiguate') as mock_disambiguate:
            mock_disambiguate.delay().id = '123'
            assert response == client.post('/api/v2/normalizeddata/', *args, **kwargs)
