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


class TestPostProviderRegistration:

    # 301 characters
    LONG_MESSAGE = (
        '3Hc0q7ZkM10seNA8lt2h20ggq8S7NxbBKvAtkAI7S2J4RJeiij'
        '8m3TMfv4TI7AXzHI8jrGnK7TlI95z75yRFvmLBfNV4KCaj6acv'
        'g22Vca8DIhmFyFrxkfRTW88WHqUvaTPDl4646AHSo7kkXrMNS2'
        'eZGfjKa8G7kcVX2OyZp2Fv3zvHiKFH9UeEnEnZAqrRTC3QSTjK'
        'DztGEwvsfQsjLzTp42pLXeFLw91y4eJ0jkgQC4KqFLwgtaD5FX'
        'RrNkZDG8HqKoQbevHbMXTYRtMjYfuJZisyv7BuWb5EhZGU7yTv'
        'a'
    )

    # 1001 characters
    LONGER_MESSAGE = (
        'OZvaNw9SZ5Z1aCSTqntvaAUEhAXEOCbcz3wYQ3c8KLTKPG6iWg'
        'q1PVZllPA0KlkfACtLvKq1s7aB61ITWJDpuBFXv9KGhMzh8WgZ'
        'jjhohpb56sOES6iTMGKuylDXKrsgVhj6EWPDWgHFCRBpFVLRYn'
        'ZHsle8s4EsqVqpOzw5mEGgmGxes8vjgoYRExRkmblu4lWMpbNy'
        'jgCpUl5oQ3l4NWpZRCHF4SuXVucZxaB8CTC9MUustkz8weEYEG'
        'xiGB7h2N1z6ZqyuLq8Y0zyXL2BmyRAuc8yHLpqBg7ncTCLuqfy'
        'iiFEu2hINuTaSjBFHv6V90MgJMq4C0HpnTMJYTMhG4cpuS767a'
        'Eu6FlirlnZvaZQaGVGiHnSj73nHj2C0SKQy8NEIX3UQbmJQ0X6'
        'sCKhSkQPHjn75InaZlNLHRUSUI1O555ITFJwJIlX0SRcYvWVy9'
        'v5LMxquRbOExuEAqczqnABQJeDRkQnVbcL2wXc6DT2PcNk0Vjc'
        'OC5xk3R47Z7eG2wllb18YZ7gAvjhL7lNAMe8xPJnloW77XCrR0'
        'OumiIvXohWLlRy36oYsQgitoUqCl94By6Z8mo5Gn7tSe6Knc6G'
        'gfz8Ym6agWnrEWjO05VLZX5x933P1vgZeu73Vs0BY1OQ5R6gff'
        'k6Rl6nSvMA5qPT4RJJClprCQSRTCANpUwoniWh4Zhp2fWxQ1Mk'
        'Jnuwv725r7HJYgEel0BIDU8kipqty2f8yQZrEDslGnc3CBk6vJ'
        'BifwaCLHhAsILbMUaLGP6T3uInH9SThPkFpvE0jo5iGYHEj3xk'
        '2TAil3ibrmDrVYw2FnWZDBWNRQbCHwMXWNQZmWkgukPPfC4m5Z'
        'uXp8f8RfKI09oI3S7ZYyGLxab83fJJgmvsIcRW3necJMyG4Qz6'
        'c5yvRkkBmuCf4cLiRJHJtfiF1MlOo5auAUbbuXFyA4foqqUbwX'
        'q6XKFR2H2U2sQQNgBtgksfPfAfT2kM8czRQHb2qBOqYus6hIgP'
        'a'
    )

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
                'type': 'ProviderRegistration',
                'attributes': {
                    'contactName': 'Test'
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
        'in': requests.Request(
            'POST',
            json={
                'data': {
                    'type': 'ProviderRegistration',
                    'attributes': {'contactName': 'Test'}
                }
            },
            headers={'Authorization': 'Foo'}
        )
    }, {
        'out': Response(400, json={'errors': [{
            'detail': 'Received document does not contain primary data',
            'source': {'pointer': '/data'}, 'status': '400'}
        ]}),
        'in': requests.Request('POST', json={'data': {}})
    }, {
        'out': Response(409, json={'errors': [{
            'detail': 'The resource object\'s type (None) is not the type that constitute the collection represented by the endpoint (ProviderRegistration).',
            'source': {'pointer': '/data'},
            'status': '409'
        }]}),
        'in': requests.Request('POST', json={
            'data': {
                'attributes': {}
            }
        })
    }, {
        'out': Response(400, json={
            'errors': [
                {
                    'detail': 'This field is required.',
                    'source': {'pointer': '/data/attributes/contactAffiliation'},
                    'status': '400'
                },
                {
                    'detail': 'This field is required.',
                    'source': {'pointer': '/data/attributes/contactEmail'},
                    'status': '400'},
                {
                    'detail': 'This field is required.',
                    'source': {'pointer': '/data/attributes/contactName'},
                    'status': '400'
                },
                {
                    'detail': 'This field is required.',
                    'source': {'pointer': '/data/attributes/sourceDescription'},
                    'status': '400'
                },
                {
                    'detail': 'This field is required.',
                    'source': {'pointer': '/data/attributes/sourceName'},
                    'status': '400'
                }
            ]
        }),
        'in': requests.Request('POST', json={
            'data': {
                'type': 'ProviderRegistration',
                'attributes': {}
            }
        })
    }, {
        'out': Response(400, json={'errors': [
            {
                'detail': 'JSON parse error - Expecting value: line 1 column 1 (char 0)',
                'source': {'pointer': '/data'},
                'status': '400'
            }
        ]}),
        'in': requests.Request('POST', data='<html!>')
    }, {
        'out': Response(400, json={'errors': [
            {
                'detail': 'Enter a valid email address.',
                'source': {'pointer': '/data/attributes/contactEmail'},
                'status': '400'
            },
        ]}),
        'in': requests.Request('POST', json={
            'data': {
                'type': 'ProviderRegistration',
                'attributes': {
                    'contact_affiliation': 'Test',
                    'contact_email': 'Bad email',
                    'contact_name': 'Test',
                    'source_description': 'Test',
                    'source_name': 'Test'
                }
            }
        })
    }, {
        'out': Response(201, keys={'data'}),
        'in': requests.Request('POST', json={
            'data': {
                'type': 'ProviderRegistration',
                'attributes': {
                    'contact_affiliation': 'Test',
                    'contact_email': 'good@email.com',
                    'contact_name': 'Test',
                    'source_description': 'Test',
                    'source_name': 'Test'
                }
            }
        })
    }, {
        'out': Response(400, json={'errors': [
            {
                'detail': 'Enter a valid URL.',
                'source': {'pointer': '/data/attributes/sourceBaseUrl'},
                'status': '400'
            }
        ]}),
        'in': requests.Request('POST', json={
            'data': {
                'type': 'ProviderRegistration',
                'attributes': {
                    'contact_affiliation': 'Test',
                    'contact_email': 'good@email.com',
                    'contact_name': 'Test',
                    'source_description': 'Test',
                    'source_name': 'Test',
                    'source_base_url': 'bad url'
                }
            }
        })
    }, {
        'out': Response(201, keys={'data'}),
        'in': requests.Request('POST', json={
            'data': {
                'type': 'ProviderRegistration',
                'attributes': {
                    'contact_affiliation': 'Test',
                    'contact_email': 'good@email.com',
                    'contact_name': 'Test',
                    'source_description': 'Test',
                    'source_name': 'Test',
                    'source_base_url': 'https://www.goodurl.com'
                }
            }
        })
    }, {
        'out': Response(400, json={'errors': [
            {
                'detail': 'Ensure this field has no more than 300 characters.',
                'source': {'pointer': '/data/attributes/contactAffiliation'},
                'status': '400'
            }, {
                'detail': 'Ensure this field has no more than 300 characters.',
                'source': {'pointer': '/data/attributes/contactName'},
                'status': '400'
            }, {
                'detail': 'Ensure this field has no more than 1000 characters.',
                'source': {'pointer': '/data/attributes/sourceAdditionalInfo'},
                'status': '400'
            }, {
                'detail': 'Ensure this field has no more than 1000 characters.',
                'source': {'pointer': '/data/attributes/sourceDescription'},
                'status': '400'
            }, {
                'detail': 'Ensure this field has no more than 300 characters.',
                'source': {'pointer': '/data/attributes/sourceDisallowedSets'},
                'status': '400'
            }, {
                'detail': 'Ensure this field has no more than 300 characters.',
                'source': {'pointer': '/data/attributes/sourceDocumentation'},
                'status': '400'
            }, {
                'detail': 'Ensure this field has no more than 300 characters.',
                'source': {'pointer': '/data/attributes/sourceName'},
                'status': '400'
            }, {
                'detail': 'Ensure this field has no more than 300 characters.',
                'source': {'pointer': '/data/attributes/sourcePreferredMetadataPrefix'},
                'status': '400'
            }, {
                'detail': 'Ensure this field has no more than 300 characters.',
                'source': {'pointer': '/data/attributes/sourceRateLimit'},
                'status': '400'
            }
        ]}),
        'in': requests.Request('POST', json={
            'data': {
                'type': 'ProviderRegistration',
                'attributes': {
                    'contact_affiliation': LONG_MESSAGE,
                    'contact_email': 'good@email.com',
                    'contact_name': LONG_MESSAGE,
                    'source_description': LONGER_MESSAGE,
                    'source_name': LONG_MESSAGE,
                    'source_rate_limit': LONG_MESSAGE,
                    'source_documentation': LONG_MESSAGE,
                    'source_preferred_metadata_prefix': LONG_MESSAGE,
                    'source_disallowed_sets': LONG_MESSAGE,
                    'source_additional_info': LONGER_MESSAGE
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

        assert response == client.post('/api/v2/registrations/', *args, **kwargs)

    @pytest.mark.django_db
    def test_get_data(self, client):
        assert client.get('/api/v2/registrations/').status_code == 401
