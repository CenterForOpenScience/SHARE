import json
import pytest
import dateutil
from unittest.mock import patch

from share.metadata_formats.sharev2_elastic import ShareV2ElasticFormatter, format_type
from share.util import IDObfuscator

from tests.factories import RawDatumFactory
from tests.factories.core import NormalizedDataFactory


TEST_CASES = [
    {
        'suid_id': 7,
        'source_name': 'SomeSource',
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
        'expected_formatted': {
            'contributors': ['Suzanne Simard', 'Mary Austi'],
            'date': '2017-03-31T05:39:48+00:00',
            'date_created': '2017-04-07T21:09:05.023090+00:00',
            'date_modified': '2017-04-07T21:09:05.023090+00:00',
            'date_updated': '2017-03-31T05:39:48+00:00',
            'id': 'encoded-7',
            'identifiers': ['http://dx.doi.org/10.5772/9813'],
            'publishers': ['InTech'],
            'retracted': False,
            'sources': ['SomeSource'],
            'title': 'The Role of Mycorrhizas in Forest Soil Stability with Climate Change',
            'type': 'creative work',
            'types': ['creative work'],
            'affiliations': [],
            'funders': [],
            'hosts': [],
            'subject_synonyms': [],
            'subjects': [],
            'tags': [],
            'lists': {
                'affiliations': [],
                'contributors': [
                    {
                        'cited_as': 'Suzanne Simard',
                        'family_name': 'Simard',
                        'given_name': 'Suzanne',
                        'identifiers': [],
                        'name': 'Suzanne Simard',
                        'order_cited': 0,
                        'relation': 'creator',
                        'type': 'person',
                        'types': ['person', 'agent'],
                    },
                    {
                        'cited_as': 'Mary Austi',
                        'family_name': 'Austi',
                        'given_name': 'Mary',
                        'identifiers': [],
                        'name': 'Mary Austi',
                        'order_cited': 1,
                        'relation': 'creator',
                        'type': 'person',
                        'types': ['person', 'agent'],
                    },
                ],
                'funders': [],
                'hosts': [],
                'lineage': [],
                'publishers': [
                    {
                        'name': 'InTech',
                        'identifiers': [],
                        'relation': 'publisher',
                        'type': 'organization',
                        'types': ['organization', 'agent'],
                    },
                ],
            },
        },
    },
    {
        'suid_id': 57,
        'source_name': 'foo',
        'normalized_datum_kwargs': {
            'data': {
                '@graph': [
                    {'@id': '_:8ae1b46cd2f341cb968fbf76c9a7f345', 'uri': 'http://dx.doi.org/10.5772/9813', '@type': 'workidentifier', 'creative_work': {'@id': '_:de04f3a34eb047e98891662b5345afd9', '@type': 'creativework'}},
                    {'@id': '_:de04f3a34eb047e98891662b5345afd9', '@type': 'creativework', 'is_deleted': True},
                ],
            },
        },
        'expected_formatted': {
            'id': 'encoded-57',
            'is_deleted': True,
        },
    },
    {
        'suid_id': 123,
        'source_name': 'osf reg',
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
        'expected_formatted': {
            'affiliations': ['Wassamatter University'],
            'contributors': ['Some Rando'],
            'date': '2019-01-23T20:34:21.633684+00:00',
            'date_created': '2020-02-02T20:20:02.020000+00:00',
            'date_modified': '2020-02-02T20:20:02.020000+00:00',
            'date_published': '2019-01-23T20:34:21.633684+00:00',
            'id': 'encoded-123',
            'identifiers': ['http://staging.osf.io/chair/'],
            'registration_type': 'Open-Ended Registration',
            'retracted': False,
            'sources': ['osf reg'],
            'subject_synonyms': [
                'bepress|Life Sciences|Biology',
            ],
            'subjects': [
                'bepress|Architecture',
                'osf reg|Custom life sciencesssss|Custom biologyyyy',
            ],
            'title': 'Assorted chair',
            'type': 'registration',
            'types': ['registration', 'publication', 'creative work'],
            'withdrawn': False,
            'funders': [],
            'hosts': [],
            'publishers': [],
            'tags': [],
            'lists': {
                'affiliations': [
                    {
                        'cited_as': 'Wassamatter University',
                        'identifiers': [],
                        'name': 'Wassamatter University',
                        'relation': 'agent work relation',
                        'type': 'institution',
                        'types': ['institution', 'organization', 'agent'],
                    },
                ],
                'contributors': [
                    {
                        'cited_as': 'Some Rando',
                        'identifiers': ['http://staging.osf.io/rando/', 'mailto:rando@example.com'],
                        'name': 'Some Rando',
                        'order_cited': 0,
                        'relation': 'creator',
                        'type': 'person',
                        'types': ['person', 'agent'],
                    },
                ],
                'lineage': [
                    {
                        'identifiers': ['http://staging.osf.io/mdept/'],
                        'title': 'Miscellaneous department',
                        'type': 'registration',
                        'types': ['registration', 'publication', 'creative work'],
                    },
                    {
                        'identifiers': ['http://staging.osf.io/vroom/'],
                        'title': 'Various room',
                        'type': 'registration',
                        'types': ['registration', 'publication', 'creative work'],
                    },
                ],
                'funders': [],
                'hosts': [],
                'publishers': [],
            },
        },
    },
]


@pytest.mark.parametrize('suid_id,source_name,normalized_datum_kwargs,expected_formatted', [
    [
        test_case['suid_id'],
        test_case['source_name'],
        test_case['normalized_datum_kwargs'],
        test_case['expected_formatted'],
    ]
    for test_case in TEST_CASES
])
@pytest.mark.django_db
@patch.object(IDObfuscator, 'encode', wraps=lambda suid: f'encoded-{suid.id}')
def test_format_sharev2_elastic(mock_encode, suid_id, source_name, normalized_datum_kwargs, expected_formatted):
    normd = NormalizedDataFactory(
        raw=RawDatumFactory(
            suid__id=suid_id,
            suid__source_config__source__long_title=source_name,
        ),
        **normalized_datum_kwargs,
    )
    actual_formatted = json.loads(ShareV2ElasticFormatter().format(normd))

    assert actual_formatted == expected_formatted


@pytest.mark.parametrize('type_name,expected', [
    ('Foo', 'foo'),
    ('FooBar', 'foo bar'),
])
def test_format_type(type_name, expected):
    actual = format_type(type_name)
    assert actual == expected
