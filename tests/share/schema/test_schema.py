import pytest

from share.schema import ShareV2Schema
from share.schema.exceptions import SchemaKeyError
from share.schema.shapes import AttributeDataType, AttributeDataFormat, RelationShape
from share.schema.shapes import ShareV2SchemaType, ShareV2SchemaAttribute, ShareV2SchemaRelation

WORK_TYPES = {
    'CreativeWork',
    'DataSet',
    'Patent',
    'Poster',
    'Publication',
    'Article',
    'Book',
    'ConferencePaper',
    'Dissertation',
    'Preprint',
    'Project',
    'Registration',
    'Report',
    'Thesis',
    'WorkingPaper',
    'Presentation',
    'Repository',
    'Retraction',
    'Software',
}

EXPLICIT_WORK_FIELDS = {
    'title',
    'description',
    'is_deleted',
    'date_published',
    'date_updated',
    'free_to_read_type',
    'free_to_read_date',
    'rights',
    'language',
    'registration_type',
    'withdrawn',
    'justification',
    'extra',
    'subjects',
    'tags',
    'related_agents',
    'related_works',
}

AGENT_TYPES = {
    'Agent',
    'Organization',
    'Consortium',
    'Department',
    'Institution',
    'Person',
}

EXPLICIT_AGENT_FIELDS = {
    'name',
    'location',
    'family_name',
    'given_name',
    'additional_name',
    'suffix',
    'extra',
    'related_agents',
    'related_works',
}


class TestStaticSchema:
    @pytest.fixture(scope='class')
    def schema(self):
        return ShareV2Schema()

    @pytest.mark.parametrize('type_name, expected', [
        ('registration', ShareV2SchemaType(
            'Registration',
            'AbstractCreativeWork',
            EXPLICIT_WORK_FIELDS,
            3,
        )),
        ('publication', ShareV2SchemaType(
            'Publication',
            'AbstractCreativeWork',
            EXPLICIT_WORK_FIELDS,
            2,
        )),
        ('creativework', ShareV2SchemaType(
            'CreativeWork',
            'AbstractCreativeWork',
            EXPLICIT_WORK_FIELDS,
            1,
        )),
        ('consortium', ShareV2SchemaType(
            'Consortium',
            'AbstractAgent',
            EXPLICIT_AGENT_FIELDS,
            3,
        )),
        ('person', ShareV2SchemaType(
            'Person',
            'AbstractAgent',
            EXPLICIT_AGENT_FIELDS,
            2,
        )),
        ('agent', ShareV2SchemaType(
            'Agent',
            'AbstractAgent',
            EXPLICIT_AGENT_FIELDS,
            1,
        )),
    ])
    def test_get_type(self, schema, type_name, expected):
        actual = schema.get_type(type_name)
        assert actual == expected

    @pytest.mark.parametrize('type_name', WORK_TYPES)
    @pytest.mark.parametrize('field_name, expected', [
        ('title', ShareV2SchemaAttribute(
            'title',
            data_type=AttributeDataType.STRING,
            data_format=None,
            is_required=False,
        )),
        ('free_to_read_type', ShareV2SchemaAttribute(
            'free_to_read_type',
            data_type=AttributeDataType.STRING,
            data_format=AttributeDataFormat.URI,
            is_required=False,
        )),
        ('extra', ShareV2SchemaAttribute(
            'extra',
            data_type=AttributeDataType.OBJECT,
            data_format=None,
            is_required=False,
        )),
        ('tags', ShareV2SchemaRelation(
            'tags',
            relation_shape=RelationShape.MANY_TO_MANY,
            related_concrete_type='Tag',
            through_concrete_type='ThroughTags',
            inverse_relation='creative_works',
            is_required=False,
            is_implicit=False,
        )),
        ('agent_relations', ShareV2SchemaRelation(
            'agent_relations',
            relation_shape=RelationShape.ONE_TO_MANY,
            related_concrete_type='AbstractAgentWorkRelation',
            inverse_relation='creative_work',
            is_required=False,
            is_implicit=True,
        )),
    ])
    def test_spot_check_work_fields(self, schema, type_name, field_name, expected):
        actual = schema.get_field(type_name, field_name)
        assert actual == expected

    @pytest.mark.parametrize('type_name', AGENT_TYPES)
    @pytest.mark.parametrize('field_name, expected', [
        ('name', ShareV2SchemaAttribute(
            'name',
            data_type=AttributeDataType.STRING,
            data_format=None,
            is_required=False,
        )),
        ('suffix', ShareV2SchemaAttribute(
            'suffix',
            data_type=AttributeDataType.STRING,
            data_format=None,
            is_required=False,
        )),
        ('identifiers', ShareV2SchemaRelation(
            'identifiers',
            relation_shape=RelationShape.ONE_TO_MANY,
            related_concrete_type='AgentIdentifier',
            inverse_relation='agent',
            is_required=False,
            is_implicit=True,
        )),
        ('related_works', ShareV2SchemaRelation(
            'related_works',
            relation_shape=RelationShape.MANY_TO_MANY,
            related_concrete_type='AbstractCreativeWork',
            through_concrete_type='AbstractAgentWorkRelation',
            inverse_relation='related_agents',
            is_required=False,
            is_implicit=False,
        )),
        ('work_relations', ShareV2SchemaRelation(
            'work_relations',
            relation_shape=RelationShape.ONE_TO_MANY,
            related_concrete_type='AbstractAgentWorkRelation',
            inverse_relation='agent',
            is_required=False,
            is_implicit=True,
        )),
    ])
    def test_spot_check_agent_fields(self, schema, type_name, field_name, expected):
        actual = schema.get_field(type_name, field_name)
        assert actual == expected

    @pytest.mark.parametrize('concrete_type, expected_type_names', (
        ('abstractcreativework', WORK_TYPES),
        ('ABSTRACTCREATIVEWORK', WORK_TYPES),
        ('abstractagent', AGENT_TYPES),
        ('tag', {'Tag'}),
        ('award', {'Award'}),
        ('throughtags', {'ThroughTags'}),
        ('Subject', {'Subject'}),
        ('throughsubjects', {'ThroughSubjects'}),
        ('throuGHAWards', {'ThroughAwards'}),
        ('award', {'Award'}),
    ))
    def test_get_type_names(self, schema, concrete_type, expected_type_names):
        type_names = schema.get_type_names(concrete_type)
        assert set(type_names) == expected_type_names

    @pytest.mark.parametrize('type_name, field_name', (
        ('preprint', 'name'),
        ('bad_type', 'bad_field'),
    ))
    def test_get_invalid_field(self, schema, type_name, field_name):
        with pytest.raises(SchemaKeyError):
            schema.get_field(type_name, field_name)

    @pytest.mark.parametrize('type_name', (
        'abstractcreativework',
        'AbstractCreativeWork',
        'bad',
        'abstractagent',
    ))
    def test_get_invalid_type(self, type_name, schema):
        with pytest.raises(SchemaKeyError):
            schema.get_type('bad')
