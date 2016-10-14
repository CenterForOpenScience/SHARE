import json
import pytest
import requests

invalid_work = {
    '@graph': [
        {
            '@type': 'InvalidWorkType',
            'title': 'Abstract Work',
            '@id': '_:1bf1bf86939d433d96402090c33251d6',
        }
    ]
}

invalid_proxy_work = {
    '@graph': [
        {
            '@type': 'AbstractCreativeWork',
            'title': 'Abstract Work',
            '@id': '_:1bf1bf86939d433d96402090c33251d6',
        }
    ]
}

valid_work_valid_entity = {
    '@graph': [
        {
            '@type': 'Publisher',
            '@id': '_:697f809c05ea4a6fba7cff3beb1ad316',
            'name': 'Publishing Group'
        },
        {
            'entity': {
                '@id': '_:697f809c05ea4a6fba7cff3beb1ad316',
                '@type': 'Publisher'
            },
            'creative_work': {
                '@id': '_:1bf1bf86939d433d96402090c33251d6',
                '@type': 'Publication'
            },
            '@id': '_:76c520ec6fe54d5097c2413886ff027e',
            '@type': 'Association'
        },
        {
            '@type': 'Publication',
            'title': 'Publisher',
            'publishers': [{
                '@id': '_:76c520ec6fe54d5097c2413886ff027e',
                '@type': 'Association'
            }],
            '@id': '_:1bf1bf86939d433d96402090c33251d6',
        }
    ]
}

valid_work_invalid_entity = {
    '@graph': [
        {
            '@type': 'Publisher',
            '@id': '_:697f809c05ea4a6fba7cff3beb1ad316',
            'name': 'Publishing Group'
        },
        {
            'entity': {
                '@id': '_:697f809c05ea4a6fba7cff3beb1ad316',
                '@type': 'Entity'
            },
            'creative_work': {
                '@id': '_:1bf1bf86939d433d96402090c33251d6',
                '@type': 'Publication'
            },
            '@id': '_:76c520ec6fe54d5097c2413886ff027e',
            '@type': 'Association'
        },
        {
            '@type': 'Publication',
            'title': 'Publisher',
            'publishers': [{
                '@id': '_:76c520ec6fe54d5097c2413886ff027e',
                '@type': 'Association'
            }],
            '@id': '_:1bf1bf86939d433d96402090c33251d6',
        }
    ]
}

valid_work_invalid_entity_field = {
    '@graph': [
        {
            '@type': 'Publisher',
            '@id': '_:697f809c05ea4a6fba7cff3beb1ad316',
            'name': 'Publishing Group',
            'isni': 'Institution field'
        },
        {
            'entity': {
                '@id': '_:697f809c05ea4a6fba7cff3beb1ad316',
                '@type': 'Publisher'
            },
            'creative_work': {
                '@id': '_:1bf1bf86939d433d96402090c33251d6',
                '@type': 'Publication'
            },
            '@id': '_:76c520ec6fe54d5097c2413886ff027e',
            '@type': 'Association'
        },
        {
            '@type': 'Publication',
            'title': 'Publisher',
            'publishers': [{
                '@id': '_:76c520ec6fe54d5097c2413886ff027e',
                '@type': 'Association'
            }],
            '@id': '_:1bf1bf86939d433d96402090c33251d6',
        }
    ]
}


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


class TestValidator:

    POST_CASES = [{
        'out': Response(400, json={'errors': {'normalized_data': ['This field is required.']}}),
        'in': requests.Request('POST', json={})
    }, {
        'out': Response(400, json={'detail': 'JSON parse error - Expected object or value'}),
        'in': requests.Request('POST', data='<html!>')
    }, {
        'out': Response(400, json={'errors': {'normalized_data': ['@graph may not be empty']}}),
        'in': requests.Request('POST', json={'normalized_data': {
            '@graph': []
        }})
    }, {
        'out': Response(202, keys={'normalized_id', 'task_id'}),
        'in': requests.Request('POST', json={'normalized_data': {
            '@graph': [{
                '@id': '_:100',
                '@type': 'Person',
                'given_name': 'Jim',
            }]
        }})
    }, {
        'out': Response(400, json={'errors': {'normalized_data': ["'@id' is a required property at /@graph/0"]}}),
        'in': requests.Request('POST', json={'normalized_data': {
            '@graph': [{
                '@type': 'Person',
                'given_name': 'Jim',
            }]
        }})
    }, {
        'out': Response(400, json={'errors': {'normalized_data': [
            "'Entity' is not one of ['FUNDER', 'Funder', " +
            "'INSTITUTION', 'Institution', 'ORGANIZATION', " +
            "'Organization', 'PUBLISHER', 'Publisher', " +
            "'funder', 'institution', 'organization', " +
            "'publisher'] at /@graph/1"]}}),
        'in': requests.Request('POST', json={'normalized_data': valid_work_invalid_entity})
    }, {
        'out': Response(400, json={'errors': {'normalized_data': ["'AbstractCreativeWork' is not a valid type"]}}),
        'in': requests.Request('POST', json={'normalized_data': invalid_proxy_work})
    }, {
        'out': Response(400, json={'errors': {'normalized_data': ["'InvalidWorkType' is not a valid type"]}}),
        'in': requests.Request('POST', json={'normalized_data': invalid_work})
    }, {
        'out': Response(202, keys={'normalized_id', 'task_id'}),
        'in': requests.Request('POST', json={'normalized_data': valid_work_valid_entity})
    }, {
        'out': Response(400, json={'errors': {'normalized_data': ["Additional properties are not allowed ('isni' was unexpected) at /@graph/0"]}}),
        'in': requests.Request('POST', json={'normalized_data': valid_work_invalid_entity_field})
    }, {
        # does not break because the raw information is not processed
        'out': Response(202, keys={'normalized_id', 'task_id'}),
        'in': requests.Request('POST', json={
            'normalized_data': valid_work_valid_entity,
            'raw': 'invalid_pk'
        })
    }]

    @pytest.mark.django_db
    @pytest.mark.parametrize('_request, response', [(case['in'], case['out']) for case in POST_CASES])
    def test_validator(self, trusted_user, client, _request, response):
        args, kwargs = (), {'content_type': 'application/json'}

        if _request.data:
            kwargs['data'] = _request.data
        elif _request.json is not None:
            kwargs['data'] = json.dumps(_request.json)

        kwargs['HTTP_AUTHORIZATION'] = 'Bearer {}'.format(trusted_user.accesstoken_set.first())

        assert response == client.post('/api/v2/normalizeddata/', *args, **kwargs)

    @pytest.mark.django_db
    def test_robot_validator(self, robot_user, raw_data_id, client):
        args, kwargs = (), {'content_type': 'application/json'}

        response = Response(202, keys={'normalized_id', 'task_id'})
        _request = requests.Request('POST', json={
            'normalized_data': valid_work_valid_entity,
            'raw': raw_data_id
        })

        if _request.data:
            kwargs['data'] = _request.data
        elif _request.json is not None:
            kwargs['data'] = json.dumps(_request.json)

        kwargs['HTTP_AUTHORIZATION'] = 'Bearer {}'.format(robot_user.accesstoken_set.first())

        assert response == client.post('/api/v2/normalizeddata/', *args, **kwargs)
