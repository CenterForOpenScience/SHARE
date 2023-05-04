import dateutil

import pytest


FORMATTER_TEST_INPUTS = {
    'mycorrhizas': {
        'suid_id': 7,
        'suid_value': 'oof',
        'source_name': 'SomeSource',
        'source_config_label': 'foo',
        'raw_datum_kwargs': {
            'date_created': dateutil.parser.isoparse('2017-04-07T21:09:05.023090+00:00'),
        },
        'normalized_datum_kwargs': {
            'created_at': dateutil.parser.isoparse('2017-04-07T21:09:05.023090+00:00'),
            'data': {
                '@graph': [
                    {'@id': '_:cfed87cc7294471eac2b67d9ce92f60b', '@type': 'person', 'given_name': 'Suzanne', 'family_name': 'Simard', 'identifiers': [], 'related_agents': []},
                    {'@id': '_:c786ef414acb423f878522690453a6b8', '@type': 'creator', 'agent': {'@id': '_:cfed87cc7294471eac2b67d9ce92f60b', '@type': 'person'}, 'cited_as': 'Suzanne Simard', 'order_cited': 0, 'creative_work': {'@id': '_:de04f3a34eb047e98891662b5345afd9', '@type': 'creativework'}},
                    {'@id': '_:2afb5767c79c47c9ab6b87c7d5b3aa0a', '@type': 'person', 'given_name': 'Mary', 'family_name': 'Austi', 'identifiers': [], 'related_agents': []},
                    {'@id': '_:44ec4e74e8ae487cbd86abcde5c2a075', '@type': 'creator', 'agent': {'@id': '_:2afb5767c79c47c9ab6b87c7d5b3aa0a', '@type': 'person'}, 'cited_as': 'Mary Austi', 'order_cited': 1, 'creative_work': {'@id': '_:de04f3a34eb047e98891662b5345afd9', '@type': 'creativework'}},
                    {'@id': '_:acfbb4f3c8314771ab718e1f42dead89', 'name': 'InTech', '@type': 'organization', 'identifiers': []},
                    {'@id': '_:e0fdb4b7b6194b699078f26a799cd232', '@type': 'publisher', 'agent': {'@id': '_:acfbb4f3c8314771ab718e1f42dead89', '@type': 'organization'}, 'creative_work': {'@id': '_:de04f3a34eb047e98891662b5345afd9', '@type': 'creativework'}},
                    {'@id': '_:8ae1b46cd2f341cb968fbf76c9a7f345', 'uri': 'http://dx.doi.org/10.5772/9813', '@type': 'workidentifier', 'creative_work': {'@id': '_:de04f3a34eb047e98891662b5345afd9', '@type': 'creativework'}},
                    {'@id': '_:de04f3a34eb047e98891662b5345afd9', 'tags': [], '@type': 'creativework', 'extra': {'type': 'book-chapter', 'member': 'http://id.crossref.org/member/3774', 'titles': ['The Role of Mycorrhizas in Forest Soil Stability with Climate Change'], 'date_created': '2012-03-29T07:53:20+00:00', 'date_published': {'date_parts': [[2010, 8, 17]]}, 'container_title': ['Climate Change and Variability'], 'published_online': {'date_parts': [[2010, 8, 17]]}}, 'title': 'The Role of Mycorrhizas in Forest Soil Stability with Climate Change', 'identifiers': [{'@id': '_:8ae1b46cd2f341cb968fbf76c9a7f345', '@type': 'workidentifier'}], 'date_updated': '2017-03-31T05:39:48+00:00', 'related_agents': [{'@id': '_:c786ef414acb423f878522690453a6b8', '@type': 'creator'}, {'@id': '_:44ec4e74e8ae487cbd86abcde5c2a075', '@type': 'creator'}, {'@id': '_:e0fdb4b7b6194b699078f26a799cd232', '@type': 'publisher'}]},
                ],
                '@context': {}
            },
        },
    },
    'no-names-only-name-parts': {
        'suid_id': 8,
        'suid_value': 'rab',
        'source_name': 'SameSource',
        'source_config_label': 'bar',
        'raw_datum_kwargs': {
            'date_created': dateutil.parser.isoparse('2017-04-07T21:09:05.023090+00:00'),
        },
        'normalized_datum_kwargs': {
            'created_at': dateutil.parser.isoparse('2017-04-07T21:09:05.023090+00:00'),
            'data': {
                '@graph': [
                    {'@id': '_:cfed87cc7294471eac2b67d9ce92f60b', '@type': 'person', 'given_name': 'Suzanne', 'family_name': 'Simard', 'identifiers': [], 'related_agents': []},
                    {'@id': '_:c786ef414acb423f878522690453a6b8', '@type': 'creator', 'agent': {'@id': '_:cfed87cc7294471eac2b67d9ce92f60b', '@type': 'person'}, 'order_cited': 0, 'creative_work': {'@id': '_:de04f3a34eb047e98891662b5345afd9', '@type': 'creativework'}},
                    {'@id': '_:2afb5767c79c47c9ab6b87c7d5b3aa0a', '@type': 'person', 'given_name': 'Mary', 'family_name': 'Austi', 'identifiers': [], 'related_agents': []},
                    {'@id': '_:44ec4e74e8ae487cbd86abcde5c2a075', '@type': 'creator', 'agent': {'@id': '_:2afb5767c79c47c9ab6b87c7d5b3aa0a', '@type': 'person'}, 'order_cited': 1, 'creative_work': {'@id': '_:de04f3a34eb047e98891662b5345afd9', '@type': 'creativework'}},
                    {'@id': '_:8ae1b46cd2f341cb968fbf76c9a7f345', 'uri': 'http://dx.doi.org/10.5772/9813', '@type': 'workidentifier', 'creative_work': {'@id': '_:de04f3a34eb047e98891662b5345afd9', '@type': 'creativework'}},
                    {'@id': '_:de04f3a34eb047e98891662b5345afd9', 'tags': [], '@type': 'creativework', 'extra': {'type': 'book-chapter', 'member': 'http://id.crossref.org/member/3774', 'titles': ['The Role of Mycorrhizas in Forest Soil Stability with Climate Change'], 'date_created': '2012-03-29T07:53:20+00:00', 'date_published': {'date_parts': [[2010, 8, 17]]}, 'container_title': ['Climate Change and Variability'], 'published_online': {'date_parts': [[2010, 8, 17]]}}, 'title': 'The Role of Mycorrhizas in Forest Soil Stability with Climate Change', 'identifiers': [{'@id': '_:8ae1b46cd2f341cb968fbf76c9a7f345', '@type': 'workidentifier'}], 'date_updated': '2017-03-31T05:39:48+00:00', 'related_agents': [{'@id': '_:c786ef414acb423f878522690453a6b8', '@type': 'creator'}, {'@id': '_:44ec4e74e8ae487cbd86abcde5c2a075', '@type': 'creator'}, {'@id': '_:e0fdb4b7b6194b699078f26a799cd232', '@type': 'publisher'}]},
                ],
                '@context': {}
            },
        },
    },
    'with-is_deleted': {
        'suid_id': 57,
        'suid_value': 'zab',
        'source_name': 'foo',
        'source_config_label': 'baz',
        'raw_datum_kwargs': {},
        'normalized_datum_kwargs': {
            'data': {
                '@graph': [
                    {'@id': '_:8ae1b46cd2f341cb968fbf76c9a7f345', 'uri': 'http://dx.doi.org/10.5772/9813', '@type': 'workidentifier', 'creative_work': {'@id': '_:de04f3a34eb047e98891662b5345afd9', '@type': 'creativework'}},
                    {'@id': '_:de04f3a34eb047e98891662b5345afd9', '@type': 'creativework', 'is_deleted': True},
                ],
            },
        },
    },
    'with-subjects': {
        'suid_id': 123,
        'suid_value': 'xuq',
        'source_name': 'osf reg',
        'source_config_label': 'subj',
        'raw_datum_kwargs': {
            'date_created': dateutil.parser.isoparse('2020-02-02T20:20:02.02+00:00'),
        },
        'normalized_datum_kwargs': {
            'created_at': dateutil.parser.isoparse('2020-02-02T20:20:02.02+00:00'),
            'data': {
                '@graph': [
                    {'@id': '_:d4723d06-063b-4b62-816b-45ae45356991', 'name': 'Some Rando', '@type': 'person'},
                    {
                        '@id': '_:0683a366-dce6-439d-8992-e96caf0c9d27',
                        'uri': 'http://staging.osf.io/rando/',
                        'host': 'staging.osf.io',
                        '@type': 'agentidentifier',
                        'agent': {
                            '@id': '_:d4723d06-063b-4b62-816b-45ae45356991',
                            '@type': 'person'
                        },
                        'scheme': 'http'
                    },
                    {
                        '@id': '_:4058232c-106f-4a2f-8700-d8c14a6c6ece',
                        '@type': 'registration',
                        'title': 'Assorted chair',
                        'withdrawn': False,
                        'is_deleted': False,
                        'date_published': '2019-01-23T20:34:21.633684+00:00',
                        'registration_type': 'Open-Ended Registration'
                    },
                    {
                        '@id': '_:759c7f4d-a0ba-42d3-aaa0-69ea11cc3cc7',
                        'uri': 'http://staging.osf.io/chair/',
                        'host': 'staging.osf.io',
                        '@type': 'workidentifier',
                        'scheme': 'http',
                        'creative_work': {
                            '@id': '_:4058232c-106f-4a2f-8700-d8c14a6c6ece',
                            '@type': 'registration'
                        }
                    },
                    {
                        '@id': '_:79f1833e-273f-453e-9f33-8e41b4c06feb',
                        'name': 'Wassamatter University',
                        '@type': 'institution'
                    },
                    {
                        '@id': '_:98fec91a-57d5-4aac-828e-05cf53f8102c',
                        '@type': 'agentworkrelation',
                        'agent': {
                            '@id': '_:79f1833e-273f-453e-9f33-8e41b4c06feb',
                            '@type': 'institution'
                        },
                        'cited_as': 'Wassamatter University',
                        'creative_work': {
                            '@id': '_:4058232c-106f-4a2f-8700-d8c14a6c6ece',
                            '@type': 'registration'
                        }
                    },
                    {
                        '@id': '_:bf8c6e89-2889-4b84-9e66-5d99843d4be4',
                        '@type': 'isaffiliatedwith',
                        'related': {
                            '@id': '_:79f1833e-273f-453e-9f33-8e41b4c06feb',
                            '@type': 'institution'
                        },
                        'subject': {
                            '@id': '_:d4723d06-063b-4b62-816b-45ae45356991',
                            '@type': 'person'
                        }
                    },
                    {
                        '@id': '_:c3ced6d4-9f80-4883-9a2c-8823cd9d3772',
                        'uri': 'mailto:rando@example.com',
                        'host': 'example.com',
                        '@type': 'agentidentifier',
                        'agent': {
                            '@id': '_:d4723d06-063b-4b62-816b-45ae45356991',
                            '@type': 'person'
                        },
                        'scheme': 'mailto'
                    },
                    {
                        '@id': '_:c99b622c-6c0a-4ce5-bdbc-2d6c52372a6a',
                        '@type': 'registration',
                        'title': 'Miscellaneous department',
                    },
                    {
                        '@id': '_:ee56a463-dcde-41a6-9621-0ac45819a0c2',
                        'uri': 'http://staging.osf.io/mdept/',
                        'host': 'staging.osf.io',
                        '@type': 'workidentifier',
                        'scheme': 'http',
                        'creative_work': {
                            '@id': '_:c99b622c-6c0a-4ce5-bdbc-2d6c52372a6a',
                            '@type': 'registration'
                        }
                    },
                    {
                        '@id': '_:ef2e1a06-76a7-46ed-95cf-413b56c4a49d',
                        '@type': 'ispartof',
                        'related': {
                            '@id': '_:c99b622c-6c0a-4ce5-bdbc-2d6c52372a6a',
                            '@type': 'registration'
                        },
                        'subject': {
                            '@id': '_:c99b622c-6c0a-4ce5-bdbc-1d6c52372a6a',
                            '@type': 'registration'
                        }
                    },
                    {
                        '@id': '_:c99b622c-6c0a-4ce5-bdbc-1d6c52372a6a',
                        '@type': 'registration',
                        'title': 'Various room',
                    },
                    {
                        '@id': '_:ee56a463-dcde-41a6-9621-9ac45819a0c2',
                        'uri': 'http://staging.osf.io/vroom/',
                        'host': 'staging.osf.io',
                        '@type': 'workidentifier',
                        'scheme': 'http',
                        'creative_work': {
                            '@id': '_:c99b622c-6c0a-4ce5-bdbc-1d6c52372a6a',
                            '@type': 'registration'
                        }
                    },
                    {
                        '@id': '_:ef2e1a06-76a7-46ed-95cf-313b56c4a49d',
                        '@type': 'ispartof',
                        'related': {
                            '@id': '_:c99b622c-6c0a-4ce5-bdbc-1d6c52372a6a',
                            '@type': 'registration'
                        },
                        'subject': {
                            '@id': '_:4058232c-106f-4a2f-8700-d8c14a6c6ece',
                            '@type': 'registration'
                        }
                    },
                    {
                        '@id': '_:fc11d92a-9784-465d-9d43-80af2a7cd83c',
                        '@type': 'creator',
                        'agent': {
                            '@id': '_:d4723d06-063b-4b62-816b-45ae45356991',
                            '@type': 'person'
                        },
                        'cited_as': 'Some Rando',
                        'order_cited': 0,
                        'creative_work': {
                            '@id': '_:4058232c-106f-4a2f-8700-d8c14a6c6ece',
                            '@type': 'registration'
                        }
                    },
                    {
                        '@id': '_:through-subj-architecture',
                        '@type': 'throughsubjects',
                        'creative_work': {
                            '@id': '_:4058232c-106f-4a2f-8700-d8c14a6c6ece',
                            '@type': 'registration'
                        },
                        'subject': {
                            '@id': '_:subj-architecture',
                            '@type': 'subject'
                        },
                    },
                    {
                        '@id': '_:subj-architecture',
                        '@type': 'subject',
                        'name': 'Architecture',
                    },
                    {
                        '@id': '_:through-subj-business',
                        '@type': 'throughsubjects',
                        'is_deleted': True,  # back-compat with a prior hack
                        'creative_work': {
                            '@id': '_:4058232c-106f-4a2f-8700-d8c14a6c6ece',
                            '@type': 'registration'
                        },
                        'subject': {
                            '@id': '_:subj-business',
                            '@type': 'subject'
                        },
                    },
                    {
                        '@id': '_:subj-business',
                        '@type': 'subject',
                        'name': 'Business',
                    },
                    {
                        '@id': '_:through-subj-education',
                        '@type': 'throughsubjects',
                        'creative_work': {
                            '@id': '_:4058232c-106f-4a2f-8700-d8c14a6c6ece',
                            '@type': 'registration'
                        },
                        'subject': {
                            '@id': '_:subj-education',
                            '@type': 'subject'
                        },
                    },
                    {
                        '@id': '_:subj-education',
                        '@type': 'subject',
                        'name': 'Education',
                        'is_deleted': True,  # back-compat with a prior hack
                    },
                    {
                        '@id': '_:through-subj-custom-biology',
                        '@type': 'throughsubjects',
                        'creative_work': {
                            '@id': '_:4058232c-106f-4a2f-8700-d8c14a6c6ece',
                            '@type': 'registration'
                        },
                        'subject': {
                            '@id': '_:subj-custom-biology',
                            '@type': 'subject'
                        },
                    },
                    {
                        '@id': '_:subj-custom-biology',
                        '@type': 'subject',
                        'name': 'Custom biologyyyy',
                        'parent': {
                            '@id': '_:subj-custom-life-sciences',
                            '@type': 'subject',
                        },
                        'central_synonym': {
                            '@id': '_:subj-central-biology',
                            '@type': 'subject',
                        },
                    },
                    {
                        '@id': '_:subj-custom-life-sciences',
                        '@type': 'subject',
                        'name': 'Custom life sciencesssss',
                        'central_synonym': {
                            '@id': '_:subj-central-life-sciences',
                            '@type': 'subject',
                        },
                    },
                    {
                        '@id': '_:subj-central-biology',
                        '@type': 'subject',
                        'name': 'Biology',
                        'parent': {
                            '@id': '_:subj-central-life-sciences',
                            '@type': 'subject',
                        },
                    },
                    {
                        '@id': '_:subj-central-life-sciences',
                        '@type': 'subject',
                        'name': 'Life Sciences',
                    },
                ],
            },
        },
    },
    'with-osf-extra': {
        'suid_id': 99,
        'suid_value': 'guidz',
        'source_name': 'OsfProbably',
        'source_config_label': 'osf.io.v2_push',
        'raw_datum_kwargs': {
            'date_created': dateutil.parser.isoparse('2017-04-07T21:09:05.023090+00:00'),
        },
        'normalized_datum_kwargs': {
            'created_at': dateutil.parser.isoparse('2017-04-07T21:09:05.023090+00:00'),
            'data': {
                '@graph': [
                    {
                        '@id': '_:p',
                        '@type': 'person',
                        'name': 'Open McOperton',
                    },
                    {
                        '@id': '_:c',
                        '@type': 'creator',
                        'agent': {'@id': '_:p', '@type': 'person'},
                        'creative_work': {'@id': '_:w', '@type': 'creativework'},
                        'cited_as': 'Open McOperton',
                        'order_cited': 0,
                    },
                    {
                        '@id': '_:i',
                        '@type': 'workidentifier',
                        'creative_work': {'@id': '_:w', '@type': 'creativework'},
                        'uri': 'https://example.com/open',
                    },
                    {
                        '@id': '_:w',
                        '@type': 'creativework',
                        'title': 'So open',
                        'date_updated': '2017-03-31T05:39:48+00:00',
                        'extra': {
                            'osf_related_resource_types': {'foo': True, 'bar': False},
                        },
                    },
                ],
                '@context': {}
            },
        },
    },
}


@pytest.fixture(scope='module', params=FORMATTER_TEST_INPUTS.keys())
def _test_key(request):
    return request.param


@pytest.fixture(scope='module')
def formatter_test_input(_test_key):
    return FORMATTER_TEST_INPUTS[_test_key]
