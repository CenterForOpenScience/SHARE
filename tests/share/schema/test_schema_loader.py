import pytest

from share.legacy_normalize.schema.exceptions import SchemaLoadError
from share.legacy_normalize.schema.loader import SchemaLoader
from share.legacy_normalize.schema.shapes import (
    ShareV2SchemaType,
    ShareV2SchemaAttribute,
    ShareV2SchemaRelation,
    AttributeDataType,
    RelationShape,
)


@pytest.mark.parametrize('bad_attribute', [
    {},
    {'name': 'foo'},
    {'name': 'foo', 'data_type': 'bad_data_type'},
    {'name': 'foo', 'data_type': 'string', 'data_format': 'bad_data_format'},
])
def test_bad_attributes(bad_attribute):
    type_spec_list = [{
        'concrete_type': 'cement',
        'attributes': [bad_attribute],
    }]
    with pytest.raises(SchemaLoadError):
        SchemaLoader(type_spec_list)


@pytest.mark.parametrize('bad_relations', [
    [{}],
    [{'name': 'foo'}],
    [{'name': 'foo', 'relation_shape': 'one_to_many'}],
    [{
        'name': 'foo',
        'relation_shape': 'one_to_many',
        'related_concrete_type': 'bad_cement',
    }],
    [
        {'name': 'foo', 'relation_shape': 'one_to_many', 'related_concrete_type': 'cement', 'inverse_relation': 'bar'},
        {'name': 'bar', 'relation_shape': 'one_to_many', 'related_concrete_type': 'cement', 'inverse_relation': 'foo'},
    ],
])
def test_bad_relations(bad_relations):
    type_spec_list = [
        {
            'concrete_type': 'cement',
            'relations': bad_relations,
        }
    ]
    with pytest.raises(SchemaLoadError):
        SchemaLoader(type_spec_list)


conflictly_type_spec_list = [{
    'concrete_type': 'cement',
    'attributes': [
        {'name': 'foo', 'data_type': 'string'},
    ],
    'relations': [
        {'name': 'foo', 'relation_shape': 'one_to_many', 'related_concrete_type': 'cement', 'inverse_relation': 'bar'},
    ]
}]


def test_conflicts():
    with pytest.raises(SchemaLoadError):
        SchemaLoader(conflictly_type_spec_list)


class TestGoodSchema:
    @pytest.fixture(scope='class')
    def loader(self):
        return SchemaLoader([{
            'concrete_type': 'cement',
            'attributes': [
                {'name': 'ash', 'data_type': 'string'},
            ],
            'relations': [
                {
                    'name': 'foo',
                    'relation_shape': 'many_to_many',
                    'related_concrete_type': 'cement',
                    'through_concrete_type': 'foobar',
                    'incoming_through_relation': 'inverse_bar',
                    'outgoing_through_relation': 'inverse_foo',
                    'inverse_relation': 'bar',
                },
                {
                    'name': 'bar',
                    'relation_shape': 'many_to_many',
                    'related_concrete_type': 'cement',
                    'through_concrete_type': 'foobar',
                    'incoming_through_relation': 'inverse_foo',
                    'outgoing_through_relation': 'inverse_bar',
                    'inverse_relation': 'foo',
                },
            ],
        }, {
            'concrete_type': 'asphalt',
            'type_tree': {
                'bitumen': {
                    'dilbit': {},
                },
                'tarmac': None,
            },
            'attributes': [
                {'name': 'gravel', 'data_type': 'integer'},
            ],
            'relations': [
                {
                    'name': 'cement',
                    'relation_shape': 'many_to_one',
                    'related_concrete_type': 'cement',
                    'inverse_relation': 'implicit_asphalts',
                },
                {
                    'name': 'cements',
                    'relation_shape': 'one_to_many',
                    'related_concrete_type': 'cement',
                    'inverse_relation': 'implicit_asphalt',
                },
            ],
        }, {
            'concrete_type': 'foobar',
            'relations': [
                {
                    'name': 'inverse_foo',
                    'relation_shape': 'many_to_one',
                    'related_concrete_type': 'cement',
                    'inverse_relation': 'foo_bars',
                },
                {
                    'name': 'inverse_bar',
                    'relation_shape': 'many_to_one',
                    'related_concrete_type': 'cement',
                    'inverse_relation': 'bar_foos',
                },
            ],
        }])

    def test_type_names(self, loader):
        assert loader.concrete_types == {'cement', 'asphalt', 'foobar'}

        # concrete type 'asphalt' has subtypes, so shouldn't be in schema_types
        actual_type_names = set(st.name for st in loader.schema_types.values())
        assert actual_type_names == {'cement', 'bitumen', 'dilbit', 'tarmac', 'foobar'}

    @pytest.mark.parametrize('type_name, expected', [
        ('cement', ShareV2SchemaType(
            'cement',
            'cement',
            {'ash', 'foo', 'bar'},
        )),
        ('bitumen', ShareV2SchemaType(
            'bitumen',
            'asphalt',
            {'gravel', 'cement', 'cements'},
            ('bitumen',),
        )),
        ('dilbit', ShareV2SchemaType(
            'dilbit',
            'asphalt',
            {'gravel', 'cement', 'cements'},
            ('dilbit', 'bitumen'),
        )),
        ('tarmac', ShareV2SchemaType(
            'tarmac',
            'asphalt',
            {'gravel', 'cement', 'cements'},
            ('tarmac',),
        )),
    ])
    def test_schema_types(self, loader, type_name, expected):
        actual = loader.schema_types[type_name]
        assert actual == expected

    @pytest.mark.parametrize('type_name, field_name, expected', [
        ('cement', 'ash', ShareV2SchemaAttribute(
            'ash',
            data_type=AttributeDataType.STRING,
            data_format=None,
            is_required=False,
        )),
        ('cement', 'foo', ShareV2SchemaRelation(
            'foo',
            relation_shape=RelationShape.MANY_TO_MANY,
            related_concrete_type='cement',
            through_concrete_type='foobar',
            incoming_through_relation='inverse_bar',
            outgoing_through_relation='inverse_foo',
            inverse_relation='bar',
        )),
        ('cement', 'bar', ShareV2SchemaRelation(
            'bar',
            relation_shape=RelationShape.MANY_TO_MANY,
            related_concrete_type='cement',
            through_concrete_type='foobar',
            incoming_through_relation='inverse_foo',
            outgoing_through_relation='inverse_bar',
            inverse_relation='foo',
        )),
        ('cement', 'implicit_asphalt', ShareV2SchemaRelation(
            'implicit_asphalt',
            relation_shape=RelationShape.MANY_TO_ONE,
            related_concrete_type='asphalt',
            inverse_relation='cements',
            is_implicit=True,
        )),
        ('cement', 'implicit_asphalts', ShareV2SchemaRelation(
            'implicit_asphalts',
            relation_shape=RelationShape.ONE_TO_MANY,
            related_concrete_type='asphalt',
            inverse_relation='cement',
            is_implicit=True,
        )),
        ('asphalt', 'gravel', ShareV2SchemaAttribute(
            'gravel',
            data_type=AttributeDataType.INTEGER,
            data_format=None,
            is_required=False,
        )),
        ('asphalt', 'cement', ShareV2SchemaRelation(
            'cement',
            relation_shape=RelationShape.MANY_TO_ONE,
            related_concrete_type='cement',
            inverse_relation='implicit_asphalts',
        )),
        ('asphalt', 'cements', ShareV2SchemaRelation(
            'cements',
            relation_shape=RelationShape.ONE_TO_MANY,
            related_concrete_type='cement',
            inverse_relation='implicit_asphalt',
        )),
    ])
    def test_schema_fields(self, loader, type_name, field_name, expected):
        actual = loader.schema_fields[(type_name, field_name)]
        assert actual == expected
