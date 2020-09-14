import pytest

from share.schema.exceptions import SchemaLoadError
from share.schema.loader import SchemaLoader
from share.schema.shapes import (
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
    [{'name': 'foo', 'relation_shape': 'many_to_many'}],
    [{'name': 'foo', 'relation_shape': 'many_to_many', 'related_concrete_type': 'bad_cement'}],
    [
        {'name': 'foo', 'relation_shape': 'many_to_many', 'related_concrete_type': 'cement', 'inverse_relation': 'bar'},
        {'name': 'bar', 'relation_shape': 'one_to_many', 'related_concrete_type': 'cement', 'inverse_relation': 'foo'},
    ],
])
def test_bad_relations(bad_relations):
    type_spec_list = [{
        'concrete_type': 'cement',
        'relations': bad_relations,
    }]
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
            'concrete_type': 'Cement',
            'attributes': [
                {'name': 'ash', 'data_type': 'string'},
            ],
            'relations': [
                {'name': 'foo', 'relation_shape': 'many_to_many', 'related_concrete_type': 'Cement', 'through_concrete_type': 'FooBar', 'inverse_relation': 'bar'},
                {'name': 'bar', 'relation_shape': 'many_to_many', 'related_concrete_type': 'Cement', 'through_concrete_type': 'FooBar', 'inverse_relation': 'foo'},
            ],
        }, {
            'concrete_type': 'Asphalt',
            'type_tree': {
                'Bitumen': {
                    'Dilbit': {},
                },
                'Tarmac': None,
            },
            'attributes': [
                {'name': 'gravel', 'data_type': 'integer'},
            ],
            'relations': [
                {'name': 'cement', 'relation_shape': 'many_to_one', 'related_concrete_type': 'Cement', 'inverse_relation': 'implicit_asphalts'},
                {'name': 'cements', 'relation_shape': 'one_to_many', 'related_concrete_type': 'Cement', 'inverse_relation': 'implicit_asphalt'},
            ],
        }, {
            'concrete_type': 'FooBar',
        }])

    def test_type_names(self, loader):
        assert loader.concrete_types == {'Cement', 'Asphalt', 'FooBar'}

        # concrete type 'asphalt' has subtypes, so shouldn't be in schema_types
        actual_type_names = set(st.name for st in loader.schema_types.values())
        assert actual_type_names == {'Cement', 'Bitumen', 'Dilbit', 'Tarmac', 'FooBar'}

    @pytest.mark.parametrize('type_name, expected', [
        ('cement', ShareV2SchemaType('Cement', 'Cement', {'ash', 'foo', 'bar'})),
        ('bitumen', ShareV2SchemaType('Bitumen', 'Asphalt', {'gravel', 'cement', 'cements'}, 1)),
        ('dilbit', ShareV2SchemaType('Dilbit', 'Asphalt', {'gravel', 'cement', 'cements'}, 2)),
        ('tarmac', ShareV2SchemaType('Tarmac', 'Asphalt', {'gravel', 'cement', 'cements'}, 1)),
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
            related_concrete_type='Cement',
            through_concrete_type='FooBar',
            inverse_relation='bar',
        )),
        ('cement', 'bar', ShareV2SchemaRelation(
            'bar',
            relation_shape=RelationShape.MANY_TO_MANY,
            related_concrete_type='Cement',
            through_concrete_type='FooBar',
            inverse_relation='foo',
        )),
        ('cement', 'implicit_asphalt', ShareV2SchemaRelation(
            'implicit_asphalt',
            relation_shape=RelationShape.MANY_TO_ONE,
            related_concrete_type='Asphalt',
            inverse_relation='cements',
            is_implicit=True,
        )),
        ('cement', 'implicit_asphalts', ShareV2SchemaRelation(
            'implicit_asphalts',
            relation_shape=RelationShape.ONE_TO_MANY,
            related_concrete_type='Asphalt',
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
            related_concrete_type='Cement',
            inverse_relation='implicit_asphalts',
        )),
        ('asphalt', 'cements', ShareV2SchemaRelation(
            'cements',
            relation_shape=RelationShape.ONE_TO_MANY,
            related_concrete_type='Cement',
            inverse_relation='implicit_asphalt',
        )),
    ])
    def test_schema_fields(self, loader, type_name, field_name, expected):
        actual = loader.schema_fields[(type_name, field_name)]
        assert actual == expected
