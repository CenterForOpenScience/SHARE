from unittest import mock
import json
import pytest
import requests

from share.util import IDObfuscator

from tests import factories


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
            'code': 'not_authenticated',
            'detail': 'Authentication credentials were not provided.',
            'source': {'pointer': '/data'},
            'status': '401'
        }]}),
        'in': requests.Request('POST', headers={'Content-Type': 'application/vnd.api+json'}, json={'data': {'type': 'NormalizedData'}})
    }, {
        'authorized': False,
        'out': Response(401, json={'errors': [{
            'code': 'not_authenticated',
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
            'code': 'not_authenticated',
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
            'code': 'parse_error',
            'detail': 'Received document does not contain primary data',
            'source': {'pointer': '/data'},
            'status': '400'
        }]}),
        'in': requests.Request('POST', headers={'Content-Type': 'application/vnd.api+json'}, json={})
    }, {
        'out': Response(400, json={'errors': [{
            'code': 'parse_error',
            'detail': 'JSON parse error - Expecting value: line 1 column 1 (char 0)',
            'source': {'pointer': '/data'},
            'status': '400'
        }]}),
        'in': requests.Request('POST', headers={'Content-Type': 'application/vnd.api+json'}, data='<html!>')
    }, {
        'out': Response(400, json={
            'errors': [
                {
                    'code': 'invalid',
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
                    'suid': 'jim',
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
        'out': Response(202, keys={'data'}),
        'in': requests.Request('POST', headers={'Content-Type': 'application/vnd.api+json'}, json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    'data': {
                        '@graph': [{
                            '@id': '_:100',
                            '@type': 'CreativeWork',
                            'title': 'Jim',
                        }, {
                            '@id': '_:101',
                            '@type': 'WorkIdentifier',
                            'creative_work': {'@type': 'CreativeWork', '@id': '_:100'},
                            # a recognizable OSF guid means no suid is required
                            'uri': 'https://osf.io/jimbo',
                        }]
                    }
                }
            }
        })
    }, {
        'out': Response(400, json={
            'errors': [
                {
                    'code': 'invalid',
                    'detail': "'suid' is a required attribute",
                    'source': {'pointer': '/data'},
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
                            '@id': '_:100',
                            '@type': 'CreativeWork',
                            'title': 'Jim',
                        }]
                    }
                }
            }
        })
    }, {
        'out': Response(400, json={
            'errors': [
                {
                    'code': 'invalid',
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
                    'suid': 'jim',
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
            kwargs['HTTP_AUTHORIZATION'] = 'Bearer {}'.format(trusted_user.oauth2_provider_accesstoken.first())

        with mock.patch('api.normalizeddata.views.digestive_tract') as mock_digestive_tract:
            mock_digestive_tract.swallow__sharev2_legacy.return_value = '123'
            assert response == client.post('/api/v2/normalizeddata/', *args, **kwargs)


@pytest.mark.django_db
class TestGetNormalizedData:

    def test_by_id(self, client):
        nd = factories.NormalizedDataFactory(data={'@graph': []})
        resp = client.get('/api/v2/normalizeddata/{}/'.format(IDObfuscator.encode(nd)))
        assert resp.status_code == 200
        assert resp.json()['data']['id'] == IDObfuscator.encode(nd)
        assert resp.json()['data']['type'] == 'NormalizedData'
        assert resp.json()['data']['attributes']['data'] == {'@graph': []}
