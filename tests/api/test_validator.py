import json
import pytest
import requests

invalid_work = {
    'data': {
        'type': 'NormalizedData',
        'attributes': {
            'data': {
                '@graph': [
                    {
                        '@type': 'InvalidWorkType',
                        'title': 'Abstract Work',
                        '@id': '_:1bf1bf86939d433d96402090c33251d6',
                    }
                ]
            }
        }
    }
}

invalid_proxy_work = {
    'data': {
        'type': 'NormalizedData',
        'attributes': {
            'data': {
                '@graph': [
                    {
                        '@type': 'AbstractCreativeWork',
                        'title': 'Abstract Work',
                        '@id': '_:1bf1bf86939d433d96402090c33251d6',
                    }
                ]
            }
        }
    }
}

valid_work_valid_entity = {
    'data': {
        'type': 'NormalizedData',
        'attributes': {
            'data': {
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
        }
    }
}

valid_work_invalid_entity = {
    'data': {
        'type': 'NormalizedData',
        'attributes': {
            'data': {
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
        }
    }
}

valid_work_invalid_entity_field = {
    'data': {
        'type': 'NormalizedData',
        'attributes': {
            'data': {
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
        }
    }
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
        'out': Response(400, json={
            'errors': [{
                'detail': 'This field is required.',
                'source': {'pointer': '/data/attributes/data'},
                'status': '400'
            }]
        }),
        'in': requests.Request('POST', json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {}
            }
        })
    }, {
        'out': Response(400, json={
            'errors': [{
                'detail': 'JSON parse error - Expecting value: line 1 column 1 (char 0)',
                'source': {'pointer': '/data'},
                'status': '400'
            }]
        }),
        'in': requests.Request('POST', data='<html!>')
    }, {
        'out': Response(400, json={
            'errors': [{
                'detail': '@graph may not be empty',
                'source': {'pointer': '/data/attributes/data'},
                'status': '400'
            }]
        }),
        'in': requests.Request('POST', json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    'data': {
                        '@graph': []
                    }
                }
            }
        })
    }, {
        'out': Response(202, keys={'data'}),
        'in': requests.Request('POST', json={
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
            'errors': [{
                'detail': "'@id' is a required property at /@graph/0",
                'source': {'pointer': '/data/attributes/data'},
                'status': '400'
            }]
        }),
        'in': requests.Request('POST', json={
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
    }, {
        'out': Response(400, json={
            'errors': [{
                'detail': "'Entity' is not one of ['FUNDER', 'Funder', 'INSTITUTION', 'Institution', 'ORGANIZATION', 'Organization', 'PUBLISHER', 'Publisher', 'funder', 'institution', 'organization', 'publisher'] at /@graph/1",
                'source': {'pointer': '/data/attributes/data'},
                'status': '400'
            }]
        }),
        'in': requests.Request('POST', json=valid_work_invalid_entity)
    }, {
        'out': Response(400, json={
            'errors': [{
                'detail': "'AbstractCreativeWork' is not a valid type",
                'source': {'pointer': '/data/attributes/data'},
                'status': '400'
            }]
        }),
        'in': requests.Request('POST', json=invalid_proxy_work)
    }, {
        'out': Response(400, json={
            'errors': [{
                'detail': "'InvalidWorkType' is not a valid type",
                'source': {'pointer': '/data/attributes/data'},
                'status': '400'
            }]
        }),
        'in': requests.Request('POST', json=invalid_work)
    }, {
        'out': Response(202, keys={'data'}),
        'in': requests.Request('POST', json=valid_work_valid_entity)
    }, {
        'out': Response(400, json={
            'errors': [{
                'detail': "Additional properties are not allowed ('isni' was unexpected) at /@graph/0",
                'source': {'pointer': '/data/attributes/data'},
                'status': '400'
            }]
        }),
        'in': requests.Request('POST', json=valid_work_invalid_entity_field)
    }]

    @pytest.mark.django_db
    @pytest.mark.parametrize('_request, response, authorized', [(case['in'], case['out'], case.get('authorized', True)) for case in POST_CASES])
    def test_validator(self, trusted_user, client, _request, response, authorized):
        args, kwargs = (), {'content_type': 'application/vnd.api+json'}

        if _request.data:
            kwargs['data'] = _request.data
        elif _request.json is not None:
            kwargs['data'] = json.dumps(_request.json)

        if authorized:
            kwargs['HTTP_AUTHORIZATION'] = 'Bearer {}'.format(trusted_user.accesstoken_set.first())

        assert response == client.post('/api/v2/normalizeddata/', *args, **kwargs)
