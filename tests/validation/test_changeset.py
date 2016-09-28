import re
import pytest

from django.core.exceptions import ValidationError

from share.models.validators import JSONLDValidator


class TestJSONLDValidator:
    CASES = [{
        'out': "'@graph' is a required property at /",
        'in': {},
    }, {
        'out': "Additional properties are not allowed ('foo' was unexpected) at /",
        'in': {'foo': 'bar', '@graph': []}
    }, {
        'out': "{} is not of type 'array' at /@graph",
        'in': {
            '@graph': {}
        }
    }, {
        'out': "1 is not of type 'array' at /@graph",
        'in': {
            '@graph': 1
        }
    }, {
        'out': "1.0 is not of type 'array' at /@graph",
        'in': {
            '@graph': 1.0
        }
    }, {
        'out': "None is not of type 'array' at /@graph",
        'in': {
            '@graph': None
        }
    }, {
        'out': "'foo' is not of type 'array' at /@graph",
        'in': {
            '@graph': 'foo'
        }
    }, {
        'out': "@graph may not be empty",
        'in': {
            '@graph': []
        }
    }, {
        'out': "'@id' is a required property at /@graph/0",
        'in': {
            '@graph': [{'@type': ''}]
        }
    }, {
        'out': "1 is not of type 'object' at /@graph/0",
        'in': {
            '@graph': [1]
        }
    }, {
        'out': "None is not of type 'object' at /@graph/1",
        'in': {
            '@graph': [{'@id': '', '@type': ''}, None]
        }
    }, {
        'out': "'@type' is a required property at /@graph/0",
        'in': {
            '@graph': [{'@id': ''}]
        }
    }, {
        'out': "'Dinosaurs' is not a valid type",
        'in': {
            '@graph': [{'@id': '', '@type': 'Dinosaurs'}]
        }
    }, {
        'out': "'Tag' is not one of ['ARTICLE', 'Article', 'BOOK', 'Book', 'CONFERENCEPAPER', 'CREATIVEWORK', 'ConferencePaper', 'CreativeWork', 'DATASET', 'DISSERTATION', 'Dataset', 'Dissertation', 'LESSON', 'Lesson', 'POSTER', 'PREPRINT', 'PRESENTATION', 'PROJECT', 'PROJECTREGISTRATION', 'Poster', 'Preprint', 'Presentation', 'Project', 'ProjectRegistration', 'REPORT', 'Report', 'SECTION', 'SOFTWARE', 'Section', 'Software', 'THESIS', 'Thesis', 'WORKINGPAPER', 'WorkingPaper', 'article', 'book', 'conferencepaper', 'creativework', 'dataset', 'dissertation', 'lesson', 'poster', 'preprint', 'presentation', 'project', 'projectregistration', 'report', 'section', 'software', 'thesis', 'workingpaper'] at /@graph/0",
        'in': {
            '@graph': [{
                '@id': '_:123',
                '@type': 'throughtags',
                'tag': {'@id': '_:789', '@type': 'Tag'},
                'creative_work': {'@id': '_:456', '@type': 'Tag'},
            }]
        }
    }, {
        'out': 'Unresolved references [{"@id": "_:456", "@type": "preprint"}, {"@id": "_:789", "@type": "tag"}]',
        'in': {
            '@graph': [{
                '@id': '_:123',
                '@type': 'throughtags',
                'tag': {'@id': '_:789', '@type': 'Tag'},
                'creative_work': {'@id': '_:456', '@type': 'Preprint'},
            }]
        }
    }, {
        'out': "'creative_work' is a required property at /@graph/0",
        'in': {
            '@graph': [{
                '@id': '_:123',
                '@type': 'throughtags',
                'tag': {'@id': '_:789', '@type': 'Tag'},
            }]
        }
    }, {
        'out': "Additional properties are not allowed ('shouldnt' was unexpected) at /@graph/0",
        'in': {
            '@graph': [{
                '@id': '_:123',
                '@type': 'throughtags',
                'shouldnt': 'behere',
                'tag': {'@id': 'id', '@type': 'tag'},
                'creative_work': {'@id': 'id', '@type': 'creativework'},
            }]
        }
    }, {
        'out': re.compile(r"^Additional properties are not allowed \('(shouldnt|pls)', '(shouldnt|pls)' were unexpected\) at /@graph/0$"),
        'in': {
            '@graph': [{
                '@id': '_:123',
                '@type': 'throughtags',
                'pls': 'toleeb',
                'shouldnt': 'behere',
                'tag': {'@id': 'id', '@type': 'tag'},
                'creative_work': {'@id': 'id', '@type': 'creativework'},
            }]
        }
    }, {
        'out': re.compile("{.+} is not valid under any of the given schemas at /@graph/0/tag$"),
        'in': {
            '@graph': [{
                '@id': '_:123',
                '@type': 'throughtags',
                'creative_work': {'@id': '_:123', '@type': 'foo'},
                'tag': {'@id': '_:123', '@type': 'foo', 'il': 'legal'}
            }]
        }
    }, {
        'out': "'extra should be a dict' is not of type 'object' at /@graph/0/extra",
        'in': {
            '@graph': [{
                '@id': '_:123',
                '@type': 'Tag',
                'name': 'A Tag',
                'extra': 'extra should be a dict'
            }]
        }
    }, {
        'out': None,
        'in': {
            '@graph': [{
                '@id': '_:123',
                '@type': 'Tag',
                'name': 'A Tag',
                'extra': {
                    'with some': 'extra data'
                }
            }]
        }
    }, {
        'out': "1 is not of type 'string' at /@graph/0",
        'in': {
            '@graph': [{
                '@id': '_:123',
                '@type': 'Tag',
                'name': 1
            }]
        }
    }, {
        'out': None,
        'in': {
            '@graph': [{
                '@id': '_:123',
                '@type': 'CreativeWork',
                'title': 'Some title',
                'description': 'description',
                'tags': [{
                    '@id': '_:456',
                    '@type': 'throughtags'
                }]
            }, {
                '@id': '_:456',
                '@type': 'throughtags',
                'tag': {'@id': '_:789', '@type': 'tag'},
                'creative_work': {'@id': '_:123', '@type': 'creativework'},
            }, {
                '@id': '_:789',
                '@type': 'tag',
                'name': 'New Tag',
            }]
        }
    }, {
        'out': "'throughtugs' is not one of ['THROUGHTAGS', 'ThroughTags', 'throughtags'] at /@graph/0",
        'in': {
            '@graph': [{
                '@id': '_:123',
                '@type': 'CreativeWork',
                'title': 'Some title',
                'description': 'description',
                'tags': [{
                    '@id': '_:456',
                    '@type': 'throughtugs'
                }]
            }, {
                '@id': '_:456',
                '@type': 'throughtags',
                'tag': {'@id': '_:789', '@type': 'tag'},
                'creative_work': {'@id': '_:123', '@type': 'creativework'},
            }, {
                '@id': '_:789',
                '@type': 'tag',
                'name': 'New Tag',
            }]
        }
    }, {
        'out': "'giraffe' is not a 'uri' at /@graph/0",
        'in': {
            '@graph': [{
                '@id': '_:123',
                '@type': 'Link',
                'url': 'giraffe',
                'type': 'misc',
            }]
        }
    }, {
        'out': None,
        'in': {
            '@graph': [{
                '@id': '_:123',
                '@type': 'Link',
                'url': 'https://share.osf.io/foo',
                'type': 'misc',
            }]
        }
    }]

    @pytest.mark.parametrize('data, message', [(case['in'], case['out']) for case in CASES])
    def test_validator(self, data, message):
        try:
            JSONLDValidator()(data)
        except ValidationError as e:
            assert message is not None, 'Raised "{}"'.format(e.args[0])
            if isinstance(message, str):
                assert message == e.args[0]
            else:
                assert message.match(e.args[0]) is not None
        else:
            assert message is None, 'No exception was raised. Expecting {}'.format(message)

    # @pytest.mark.parametrize('data, message', [(case['in'], case['out']) for case in CASES])
    # def test_benchmark_validator(self, benchmark, data, message):
    #     benchmark(self.test_validator, data, message)
