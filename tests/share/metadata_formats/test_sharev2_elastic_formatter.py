import json
import pytest
from unittest.mock import patch

from share.metadata_formats.sharev2_elastic import format_type

from tests.share.metadata_formats.base import BaseMetadataFormatterTest


@pytest.mark.parametrize('type_name,expected', [
    ('Foo', 'foo'),
    ('FooBar', 'foo bar'),
])
def test_format_type(type_name, expected):
    actual = format_type(type_name)
    assert actual == expected


def fake_id_encode(obj):
    return f'encoded-{obj.id}'


class TestSharev2ElasticFormatter(BaseMetadataFormatterTest):
    @pytest.fixture(scope='class', autouse=True)
    def patch_encode(self):
        with patch('share.util.IDObfuscator.encode', wraps=fake_id_encode):
            yield

    def assert_formatter_outputs_equal(self, actual_output, expected_output):
        assert json.loads(actual_output) == expected_output

    formatter_key = 'sharev2_elastic'

    expected_outputs = {
        'mycorrhizas': {
            'contributors': ['Suzanne Simard', 'Mary Austi'],
            'date': '2017-03-31T05:39:48+00:00',
            'date_created': '2017-04-07T21:09:05.023090+00:00',
            'date_modified': '2017-04-07T21:09:05.023090+00:00',
            'date_updated': '2017-03-31T05:39:48+00:00',
            'id': 'encoded-7',
            'identifiers': ['http://dx.doi.org/10.5772/9813'],
            'publishers': ['InTech'],
            'retracted': False,
            'source_config': 'foo',
            'source_unique_id': 'oof',
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
        'no-names-only-name-parts': {
            'contributors': ['Suzanne Simard', 'Mary Austi'],
            'date': '2017-03-31T05:39:48+00:00',
            'date_created': '2017-04-07T21:09:05.023090+00:00',
            'date_modified': '2017-04-07T21:09:05.023090+00:00',
            'date_updated': '2017-03-31T05:39:48+00:00',
            'id': 'encoded-8',
            'identifiers': ['http://dx.doi.org/10.5772/9813'],
            'publishers': [],
            'retracted': False,
            'source_config': 'bar',
            'source_unique_id': 'rab',
            'sources': ['SameSource'],
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
                'publishers': [],
            },
        },
        'with-is_deleted': {
            'id': 'encoded-57',
            'is_deleted': True,
        },
        'with-subjects': {
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
            'source_config': 'subj',
            'source_unique_id': 'xuq',
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
        'with-osf-extra': {
            'affiliations': [],
            'contributors': ['Open McOperton'],
            'date': '2017-03-31T05:39:48+00:00',
            'date_created': '2017-04-07T21:09:05.023090+00:00',
            'date_modified': '2017-04-07T21:09:05.023090+00:00',
            'date_updated': '2017-03-31T05:39:48+00:00',
            'id': 'encoded-99',
            'identifiers': ['https://example.com/open'],
            'source_config': 'osf.io.v2_push',
            'source_unique_id': 'guidz',
            'sources': ['OsfProbably'],
            'subject_synonyms': [],
            'subjects': [],
            'title': 'So open',
            'type': 'creative work',
            'types': ['creative work'],
            'retracted': False,
            'funders': [],
            'hosts': [],
            'publishers': [],
            'tags': [],
            'osf_related_resource_types': {
                'foo': True,
                'bar': False,
            },
            'lists': {
                'affiliations': [],
                'contributors': [
                    {
                        'cited_as': 'Open McOperton',
                        'identifiers': [],
                        'name': 'Open McOperton',
                        'order_cited': 0,
                        'relation': 'creator',
                        'type': 'person',
                        'types': ['person', 'agent'],
                    },
                ],
                'lineage': [],
                'funders': [],
                'hosts': [],
                'publishers': [],
            },
        },
    }
