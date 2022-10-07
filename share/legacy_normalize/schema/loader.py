from share.legacy_normalize.schema.exceptions import SchemaLoadError
from share.legacy_normalize.schema.shapes import (
    RelationShape,
    AttributeDataType,
    AttributeDataFormat,
    ShareV2SchemaAttribute,
    ShareV2SchemaRelation,
    ShareV2SchemaType,
)


class SchemaLoader:
    def __init__(self, type_spec_list):
        self.schema_types = {}
        self.schema_fields = {}
        self.explicit_field_names = {}

        try:
            self.concrete_types = set(
                type_spec['concrete_type']
                for type_spec in type_spec_list
            )
            self._load_all_attrs_and_relations(type_spec_list)
            self._load_types(type_spec_list)
        except KeyError as error:
            raise SchemaLoadError(error)

    def _load_all_attrs_and_relations(self, type_spec_list):
        for type_spec in type_spec_list:
            concrete_type = type_spec['concrete_type']
            self._load_attributes(concrete_type, type_spec.get('attributes', []))
            self._load_relations(concrete_type, type_spec.get('relations', []))

    def _load_types(self, type_spec_list):
        # assumes load_all_attrs_and_relations has already been called
        for type_spec in type_spec_list:
            concrete_type = type_spec['concrete_type']
            type_tree = type_spec.get('type_tree', None)

            if type_tree:
                self._add_type_tree(concrete_type, type_tree)
            else:
                self._add_type(concrete_type, concrete_type)

    def _load_attributes(self, concrete_type, attr_list):
        for attr_dict in attr_list:
            attr = self._build_attribute(attr_dict)
            self._add_field(concrete_type, attr)

    def _load_relations(self, concrete_type, relation_list):
        for relation_dict in relation_list:
            relation = self._build_relation(relation_dict)
            self._add_relation(concrete_type, relation)
            if relation.inverse_relation:
                self._add_inverse_relation(concrete_type, relation)

    def _add_inverse_relation(self, concrete_type, relation):
        inverse_relation_shape = {
            RelationShape.MANY_TO_MANY: RelationShape.MANY_TO_MANY,
            RelationShape.MANY_TO_ONE: RelationShape.ONE_TO_MANY,
            RelationShape.ONE_TO_MANY: RelationShape.MANY_TO_ONE,
        }[relation.relation_shape]

        inverse_relation = ShareV2SchemaRelation(
            name=relation.inverse_relation,
            relation_shape=inverse_relation_shape,
            related_concrete_type=concrete_type,

            # same through type, but flip incoming/outgoing relations
            through_concrete_type=relation.through_concrete_type,
            incoming_through_relation=relation.outgoing_through_relation,
            outgoing_through_relation=relation.incoming_through_relation,

            inverse_relation=relation.name,
            is_implicit=True,
        )
        self._add_relation(relation.related_concrete_type, inverse_relation)

    def _add_type(self, concrete_type, type_name, type_lineage=()):
        self.schema_types[type_name.lower()] = ShareV2SchemaType(
            name=type_name,
            concrete_type=concrete_type,
            explicit_fields=set(self.explicit_field_names.get(concrete_type, [])),
            type_lineage=type_lineage,
        )

    def _add_type_tree(self, concrete_type, type_tree, parent_type_lineage=()):
        for type_name, subtree in type_tree.items():
            type_lineage = (type_name, *parent_type_lineage)
            self._add_type(concrete_type, type_name, type_lineage)
            if subtree:
                self._add_type_tree(concrete_type, subtree, type_lineage)

    def _add_relation(self, concrete_type, relation):
        key = (concrete_type.lower(), relation.name.lower())
        existing_relation = self.schema_fields.get(key, None)
        if existing_relation:
            is_existing_relation_compatible = (
                existing_relation.is_relation
                and relation.name == existing_relation.name
                and relation.relation_shape == existing_relation.relation_shape
                and relation.related_concrete_type == existing_relation.related_concrete_type
                and relation.through_concrete_type == existing_relation.through_concrete_type
                and relation.incoming_through_relation == existing_relation.incoming_through_relation
                and relation.outgoing_through_relation == existing_relation.outgoing_through_relation
                and relation.inverse_relation == existing_relation.inverse_relation
            )
            if not is_existing_relation_compatible:
                raise SchemaLoadError(f'relation defined two incompatible ways -- maybe a bad inverse? existing: {existing_relation}  trying to add: {relation}')

            if existing_relation.is_implicit:
                # let the new relation overwrite the implicit one
                del self.schema_fields[key]
            elif relation.is_implicit:
                return  # no need to do anything -- the same relation already exists
            else:
                raise SchemaLoadError(f'conflicting explicit relations (new: {relation} existing: {existing_relation})')

        self._add_field(concrete_type, relation)

    def _add_field(self, concrete_type, attr_or_relation):
        if concrete_type not in self.concrete_types:
            raise SchemaLoadError(f'invalid concrete_type ({concrete_type}) on field {attr_or_relation}')
        key = (concrete_type.lower(), attr_or_relation.name.lower())
        if key in self.schema_fields:
            raise SchemaLoadError(f'field defined twice: {key}')
        self.schema_fields[key] = attr_or_relation
        if not getattr(attr_or_relation, 'is_implicit', False):
            self.explicit_field_names.setdefault(concrete_type, []).append(attr_or_relation.name)

    def _build_attribute(self, attr_dict):
        return ShareV2SchemaAttribute(
            # required
            name=attr_dict['name'],
            data_type=AttributeDataType[attr_dict['data_type'].upper()],

            # optional
            is_required=attr_dict.get('is_required', False),
            data_format=AttributeDataFormat[attr_dict['data_format'].upper()] if 'data_format' in attr_dict else None,
        )

    def _build_relation(self, relation_dict):
        new_relation = ShareV2SchemaRelation(
            # required
            name=relation_dict['name'],
            relation_shape=RelationShape[relation_dict['relation_shape'].upper()],
            related_concrete_type=relation_dict['related_concrete_type'],

            # optional
            through_concrete_type=relation_dict.get('through_concrete_type', None),
            incoming_through_relation=relation_dict.get('incoming_through_relation', None),
            outgoing_through_relation=relation_dict.get('outgoing_through_relation', None),
            inverse_relation=relation_dict.get('inverse_relation', None),
            is_required=relation_dict.get('is_required', False),
        )
        if new_relation.related_concrete_type not in self.concrete_types:
            raise SchemaLoadError(f'invalid related_concrete_type on relation {new_relation}')
        if new_relation.through_concrete_type and new_relation.through_concrete_type not in self.concrete_types:
            raise SchemaLoadError(f'invalid through_concrete_type on relation {new_relation}')

        required_m2m_attrs = {
            'through_concrete_type',
            'incoming_through_relation',
            'outgoing_through_relation',
        }
        present_m2m_attrs = {
            attr_name
            for attr_name in required_m2m_attrs
            if getattr(new_relation, attr_name)
        }
        if present_m2m_attrs and new_relation.relation_shape != RelationShape.MANY_TO_MANY:
            raise SchemaLoadError(f'{present_m2m_attrs} set on non-m2m relation {new_relation}')
        if new_relation.relation_shape == RelationShape.MANY_TO_MANY and len(present_m2m_attrs) != len(required_m2m_attrs):
            missing_m2m_attrs = required_m2m_attrs - present_m2m_attrs
            raise SchemaLoadError(f'm2m relation {new_relation} missing required attrs {missing_m2m_attrs}')
        return new_relation
