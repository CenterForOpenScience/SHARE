import json
import pytest
import requests
from unittest import mock

from tests import factories

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

valid_work_valid_agent = {
    'data': {
        'type': 'NormalizedData',
        'attributes': {
            'data': {
                '@graph': [
                    {
                        '@type': 'Organization',
                        '@id': '_:697f809c05ea4a6fba7cff3beb1ad316',
                        'name': 'Publishing Group'
                    },
                    {
                        'agent': {
                            '@id': '_:697f809c05ea4a6fba7cff3beb1ad316',
                            '@type': 'Organization'
                        },
                        'creative_work': {
                            '@id': '_:1bf1bf86939d433d96402090c33251d6',
                            '@type': 'Article'
                        },
                        '@id': '_:76c520ec6fe54d5097c2413886ff027e',
                        '@type': 'Publisher'
                    },
                    {
                        '@type': 'Article',
                        'title': 'Published article',
                        'related_agents': [{
                            '@id': '_:76c520ec6fe54d5097c2413886ff027e',
                            '@type': 'Publisher'
                        }],
                        '@id': '_:1bf1bf86939d433d96402090c33251d6',
                    }
                ]
            }
        }
    }
}

valid_work_invalid_agent = {
    'data': {
        'type': 'NormalizedData',
        'attributes': {
            'data': {
                '@graph': [
                    {
                        '@type': 'Organization',
                        '@id': '_:697f809c05ea4a6fba7cff3beb1ad316',
                        'name': 'Publishing Group'
                    },
                    {
                        'agent': {
                            '@id': '_:697f809c05ea4a6fba7cff3beb1ad316',
                            '@type': 'AbstractAgent',
                        },
                        'creative_work': {
                            '@id': '_:1bf1bf86939d433d96402090c33251d6',
                            '@type': 'Article'
                        },
                        '@id': '_:76c520ec6fe54d5097c2413886ff027e',
                        '@type': 'Publisher'
                    },
                    {
                        '@type': 'Article',
                        'title': 'Publisher',
                        'related_agents': [{
                            '@id': '_:76c520ec6fe54d5097c2413886ff027e',
                            '@type': 'Organization'
                        }],
                        '@id': '_:1bf1bf86939d433d96402090c33251d6',
                    }
                ]
            }
        }
    }
}

valid_work_invalid_agent_field = {
    'data': {
        'type': 'NormalizedData',
        'attributes': {
            'data': {
                '@graph': [
                    {
                        '@type': 'Organization',
                        '@id': '_:697f809c05ea4a6fba7cff3beb1ad316',
                        'name': 'Publishing Group',
                        'family_name': 'Person Field'
                    },
                    {
                        'agent': {
                            '@id': '_:697f809c05ea4a6fba7cff3beb1ad316',
                            '@type': 'Organization'
                        },
                        'creative_work': {
                            '@id': '_:1bf1bf86939d433d96402090c33251d6',
                            '@type': 'Article'
                        },
                        '@id': '_:76c520ec6fe54d5097c2413886ff027e',
                        '@type': 'Publisher'
                    },
                    {
                        '@type': 'Article',
                        'title': 'Published',
                        'publishers': [{
                            '@id': '_:76c520ec6fe54d5097c2413886ff027e',
                            '@type': 'Publisher'
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
                'detail': "'AbstractAgent' is not one of ["
                          "'AGENT', 'Agent', 'CONSORTIUM', 'Consortium', "
                          "'DEPARTMENT', 'Department', "
                          "'INSTITUTION', 'Institution', 'ORGANIZATION', "
                          "'Organization', 'PERSON', 'Person', 'agent', "
                          "'consortium', 'department', 'institution', 'organization', 'person'"
                          "] at /@graph/1",
                'source': {'pointer': '/data/attributes/data'},
                'status': '400'
            }]
        }),
        'in': requests.Request('POST', json=valid_work_invalid_agent)
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
        'in': requests.Request('POST', json=valid_work_valid_agent)
    }, {
        'out': Response(400, json={
            'errors': [{
                'detail': "Additional properties are not allowed ('family_name' was unexpected) at /@graph/0",
                'source': {'pointer': '/data/attributes/data'},
                'status': '400'
            }]
        }),
        'in': requests.Request('POST', json=valid_work_invalid_agent_field)
    }, {
        'out': Response(400, json={'errors': [{
            'detail': "Additional properties are not allowed ('family_name' was unexpected) at /@graph/0",
            'source': {'pointer': '/data/attributes/data'},
            'status': '400'
        }]}),
        'in': requests.Request('POST', json=valid_work_invalid_agent_field)
    }, {
        # does not break because the raw information is not processed
        'out': Response(202, keys={'data'}),
        'in': requests.Request('POST', json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    'raw': {'type': 'RawData', 'id': 'invalid_id'},
                    'data': valid_work_valid_agent['data']['attributes']['data']
                }
            }
        })
    }, {
        # does not break because the task information is not processed
        'out': Response(202, keys={'data'}),
        'in': requests.Request('POST', json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    'tasks': ['invalid_task'],
                    'data': valid_work_valid_agent['data']['attributes']['data']
                }
            }
        })
    }]

    @pytest.mark.django_db
    @pytest.mark.parametrize('_request, response', [(case['in'], case['out']) for case in POST_CASES])
    def test_validator(self, trusted_user, client, _request, response):
        args, kwargs = (), {'content_type': 'application/vnd.api+json'}

        if _request.data:
            kwargs['data'] = _request.data
        elif _request.json is not None:
            kwargs['data'] = json.dumps(_request.json)

        kwargs['HTTP_AUTHORIZATION'] = 'Bearer {}'.format(trusted_user.accesstoken_set.first())

        with mock.patch('api.views.workflow.disambiguate') as mock_disambiguate:
            mock_disambiguate.delay().id = '123'
            assert response == client.post('/api/v2/normalizeddata/', *args, **kwargs)

    @pytest.mark.django_db
    def test_robot_validator(self, robot_user, raw_data_id, client):
        args, kwargs = (), {'content_type': 'application/vnd.api+json'}

        normalizer_task = factories.CeleryTaskResultFactory()

        _request = requests.Request('POST', json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    'tasks': [normalizer_task.id],
                    'raw': {'type': 'RawData', 'id': raw_data_id},
                    'data': valid_work_valid_agent['data']['attributes']['data']
                }
            }
        })

        if _request.data:
            kwargs['data'] = _request.data
        elif _request.json is not None:
            kwargs['data'] = json.dumps(_request.json)

        kwargs['HTTP_AUTHORIZATION'] = 'Bearer {}'.format(robot_user.accesstoken_set.first())

        with mock.patch('api.views.workflow.disambiguate') as mock_disambiguate:
            mock_disambiguate.delay().id = '123'
            response = client.post('/api/v2/normalizeddata/', *args, **kwargs)

        assert response.status_code == 202
        assert response.json()['data']['id'] is not None
        assert response.json()['data']['type'] == 'NormalizedData'
        assert response.json()['data']['attributes'].keys() == {'task'}
