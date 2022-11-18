import yaml
from typing import Set, Union

from share.legacy_normalize.schema.exceptions import SchemaKeyError
from share.legacy_normalize.schema.loader import SchemaLoader
from share.legacy_normalize.schema.shapes import (
    ShareV2SchemaType,
    ShareV2SchemaAttribute,
    ShareV2SchemaRelation,
)


class ShareV2Schema:
    # will be loaded only once
    _schema_types = None
    _schema_type_names = None
    _schema_fields = None

    @classmethod
    def load_schema(cls):
        with open('share/legacy_normalize/schema/schema-spec.yaml') as fobj:
            type_spec_list = yaml.load(fobj, Loader=yaml.CLoader)
        loader = SchemaLoader(type_spec_list)
        cls._schema_types = loader.schema_types
        cls._schema_fields = loader.schema_fields

        cls._schema_type_names = {
            concrete_type.lower(): {
                schema_type.name
                for schema_type in loader.schema_types.values()
                if schema_type.concrete_type == concrete_type
            }
            for concrete_type in loader.concrete_types
        }

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

    @property
    def schema_type_names(self):
        if ShareV2Schema._schema_type_names is None:
            ShareV2Schema.load_schema()
        return ShareV2Schema._schema_type_names

    def get_type(self, type_name) -> ShareV2SchemaType:
        try:
            return self.schema_types[type_name.lower()]
        except KeyError:
            raise SchemaKeyError(f'type "{type_name}" not found in SHARE schema')

    def get_field(self, type_name, field_name) -> Union[ShareV2SchemaAttribute, ShareV2SchemaRelation]:
        if type_name.lower() in self.schema_type_names:
            concrete_type = type_name
        else:
            concrete_type = self.get_type(type_name).concrete_type
        key = (concrete_type.lower(), field_name.lower())
        try:
            return self.schema_fields[key]
        except KeyError:
            raise SchemaKeyError(f'field "{type_name}.{field_name}" not found in SHARE schema')

    def get_type_names(self, concrete_type) -> Set[str]:
        try:
            return self.schema_type_names[concrete_type.lower()]
        except KeyError:
            raise SchemaKeyError(f'concrete type "{concrete_type}" not found in SHARE schema')
