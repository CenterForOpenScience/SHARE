import yaml
from typing import Set, Union

from share.schema.exceptions import SchemaKeyError
from share.schema.loader import SchemaLoader
from share.schema.shapes import (
    ShareV2SchemaType,
    ShareV2SchemaAttribute,
    ShareV2SchemaRelation,
)


class ShareV2Schema:
    _schema_types = None  # singleton
    _schema_fields = None  # singleton

    @classmethod
    def load_schema(cls):
        with open('share/schema/schema-spec.yaml') as fobj:
            type_spec_list = yaml.load(fobj)
        loader = SchemaLoader(type_spec_list)
        cls._schema_types = loader.schema_types
        cls._schema_fields = loader.schema_fields

    @property
    def schema_types(self):
        if ShareV2Schema._schema_types is None:
            ShareV2Schema.load_schema()
        return ShareV2Schema._schema_types

    @property
    def schema_fields(self):
        if ShareV2Schema._schema_fields is None:
            ShareV2Schema.load_schema()
        return ShareV2Schema._schema_fields

    def get_type(self, type_name) -> ShareV2SchemaType:
        try:
            return self.schema_types[type_name.lower()]
        except KeyError:
            raise SchemaKeyError(f'type "{type_name}" not found in SHARE schema')

    def get_field(self, type_name, field_name) -> Union[ShareV2SchemaAttribute, ShareV2SchemaRelation]:
        concrete_type = self.get_type(type_name).concrete_type
        key = (concrete_type, field_name.lower())
        try:
            return self.schema_fields[key]
        except KeyError:
            raise SchemaKeyError(f'field "{type_name}.{field_name}" not found in SHARE schema')

    def get_type_names(self, concrete_type) -> Set[str]:
        lower_concrete_type = concrete_type.lower()
        return {
            schema_type.name
            for schema_type in self.schema_types.values()
            if schema_type.concrete_type == lower_concrete_type
        }
