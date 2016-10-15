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
        'out': Response(401, json={'detail': 'Authentication credentials were not provided.'}),
        'in': requests.Request('POST', data=None)
    }, {
        'authorized': False,
        'out': Response(401, json={'detail': 'Authentication credentials were not provided.'}),
        'in': requests.Request('POST', json={'Foo': 'bar'})
    }, {
        'authorized': False,
        'out': Response(401, json={'detail': 'Authentication credentials were not provided.'}),
        'in': requests.Request('POST', json={'@graph': [{'@type': 'person', 'given_name': 'Jim'}]})
    }, {
        'authorized': False,
        'out': Response(401, json={'detail': 'Authentication credentials were not provided.'}),
        'in': requests.Request('POST', json={'@graph': [{'@type': 'person', 'given_name': 'Jim'}]}, headers={'Authorization': 'Foo'})
    }]

    @pytest.mark.django_db
    @pytest.mark.parametrize('_request, response, authorized', [(case['in'], case['out'], case.get('authorized', True)) for case in POST_CASES])
    def test_post_data(self, trusted_user, client, _request, response, authorized):
        args, kwargs = (), {'content_type': 'application/json'}

        if _request.data:
            kwargs['data'] = _request.data
        elif _request.json is not None:
            kwargs['data'] = json.dumps(_request.json)

        if authorized:
            kwargs['HTTP_AUTHORIZATION'] = 'Bearer {}'.format(trusted_user.accesstoken_set.first())

        assert response == client.post('/api/v2/normalizeddata/', *args, **kwargs)
