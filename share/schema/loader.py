from share.schema.exceptions import SchemaLoadError
from share.schema.shapes import (
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
                type_spec['concrete_type'].lower()
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
            inverse_relation=relation.name,
            is_implicit=True,
        )
        self._add_relation(relation.related_concrete_type, inverse_relation)

    def _add_type(self, concrete_type, type_name, distance_from_concrete_type=0):
        lower_name = type_name.lower()
        self.schema_types[lower_name] = ShareV2SchemaType(
            name=lower_name,
            concrete_type=concrete_type,
            distance_from_concrete_type=distance_from_concrete_type,
            explicit_fields=set(self.explicit_field_names.get(concrete_type, [])),
        )

    def _add_type_tree(self, concrete_type, type_tree, depth=1):
        for type_name, subtree in type_tree.items():
            self._add_type(concrete_type, type_name, depth)
            if subtree:
                self._add_type_tree(concrete_type, subtree, depth + 1)

    def _add_relation(self, concrete_type, relation):
        key = (concrete_type, relation.name)
        existing_relation = self.schema_fields.get(key, None)
        if existing_relation:
            is_existing_relation_compatible = (
                existing_relation.is_relation
                and relation.name == existing_relation.name
                and relation.relation_shape == existing_relation.relation_shape
                and relation.related_concrete_type == existing_relation.related_concrete_type
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
        name = attr_or_relation.name.lower()
        key = (concrete_type, name)
        if key in self.schema_fields:
            raise SchemaLoadError(f'field defined twice: {key}')
        self.schema_fields[key] = attr_or_relation
        if not getattr(attr_or_relation, 'is_implicit', False):
            self.explicit_field_names.setdefault(concrete_type, []).append(name)

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
        inverse_relation = relation_dict.get('inverse_relation', None)
        new_relation = ShareV2SchemaRelation(
            # required
            name=relation_dict['name'].lower(),
            relation_shape=RelationShape[relation_dict['relation_shape'].upper()],
            related_concrete_type=relation_dict['related_concrete_type'].lower(),

            # optional
            inverse_relation=inverse_relation.lower() if inverse_relation else None,
            is_required=relation_dict.get('is_required', False),
        )
        if new_relation.related_concrete_type not in self.concrete_types:
            raise SchemaLoadError(f'invalid related_concrete_type on relation {new_relation}')
        return new_relation
