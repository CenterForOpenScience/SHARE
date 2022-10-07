import os
import json
from collections import OrderedDict
from itertools import chain

from jsonschema import exceptions
from jsonschema import Draft4Validator, draft4_format_checker

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

from share.legacy_normalize.schema import ShareV2Schema
from share.legacy_normalize.schema.exceptions import SchemaKeyError
from share.legacy_normalize.schema.shapes import AttributeDataType, AttributeDataFormat, RelationShape
from share.legacy_normalize.transform.chain.links import IRILink
from share.legacy_normalize.transform.chain.exceptions import InvalidIRI


def is_valid_jsonld(value):
    raise Exception('Deprecated; use JSONLDValidator')


@deconstructible
class JSONLDValidator:

    __json_schema_cache = {}
    __validator_cache = {}

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jsonld-schema.json')) as fobj:
        jsonld_schema = Draft4Validator(json.load(fobj))

    db_type_map = {
        AttributeDataType.STRING: 'string',
        AttributeDataType.BOOLEAN: 'boolean',
        AttributeDataType.INTEGER: 'integer',
        AttributeDataType.DATETIME: 'string',
        AttributeDataType.OBJECT: 'object',
    }

    def __init__(self, check_existence=True):
        self.__check_existence = check_existence

    def __call__(self, value):
        try:
            JSONLDValidator.jsonld_schema.validate(value)
        except exceptions.ValidationError as e:
            raise ValidationError('{} at /{}'.format(e.message, '/'.join(str(x) for x in e.path)))

        if len(value['@graph']) < 1:
            raise ValidationError('@graph may not be empty')

        refs = {'blank': set(), 'concrete': set()}
        nodes = {'blank': set(), 'concrete': set()}
        for i, node in enumerate(value['@graph']):
            try:
                self.validate_node(node, refs, nodes)
            except exceptions.ValidationError as e:
                e.path.appendleft(i)  # Hack to add in a leading slash
                raise ValidationError('{} at /@graph/{}'.format(e.message, '/'.join(str(x) for x in e.path)))

        if refs['blank'] - nodes['blank']:
            raise ValidationError('Unresolved references {}'.format(json.dumps([
                OrderedDict([('@id', id), ('@type', type)]) for id, type in
                sorted(refs['blank'] - nodes['blank'])
            ])))

    def __eq__(self, other):
        return self.__check_existence == other.__check_existence

    def validate_node(self, value, refs, nodes):
        try:
            schema_type = ShareV2Schema().get_type(value['@type'])
        except SchemaKeyError:
            raise ValidationError("'{}' is not a valid type".format(value['@type']))

        self.validator_for(schema_type).validate(value)

        for key, val in value.items():
            if not isinstance(val, dict) or key == 'extra':
                continue

            if val['@id'].startswith('_:'):
                refs['blank'].add((val['@id'], val['@type'].lower()))
            else:
                refs['concrete'].add((val['@id'], val['@type'].lower()))

        if value['@id'].startswith('_:'):
            nodes['blank'].add((value['@id'], value['@type'].lower()))
        else:
            nodes['concrete'].add((value['@id'], value['@type'].lower()))

    def json_schema_for_field(self, share_field):
        if share_field.is_relation:
            if share_field.relation_shape == RelationShape.MANY_TO_MANY:
                concrete_type = share_field.through_concrete_type
            else:
                concrete_type = share_field.related_concrete_type

            rel = {
                'type': 'object',
                'description': getattr(share_field, 'description', ''),
                'required': ['@id', '@type'],
                'additionalProperties': False,
                'properties': {
                    '@id': {'type': ['string', 'integer']},
                    # Sorted so the same error message is sent back every time
                    '@type': {'enum': sorted(chain(*[
                        # ideally would be case-insensitive, but jsonschema enums don't know how.
                        # instead, allow 'FooBar', 'foobar', and 'FOOBAR' casings
                        (type_name, type_name.lower(), type_name.upper())
                        for type_name in ShareV2Schema().get_type_names(concrete_type)
                    ]))}
                }
            }
            if share_field.relation_shape in (RelationShape.MANY_TO_MANY, RelationShape.ONE_TO_MANY):
                return {'type': 'array', 'items': rel}
            return rel

        schema = {
            'type': JSONLDValidator.db_type_map[share_field.data_type],
            'description': getattr(share_field, 'description', ''),
        }
        if share_field.data_format == AttributeDataFormat.URI:
            schema['format'] = 'uri'

        return schema

    def json_schema_for_type(self, share_schema_type):
        if share_schema_type.name in JSONLDValidator.__json_schema_cache:
            return JSONLDValidator.__json_schema_cache[share_schema_type.name]

        schema = {
            'type': 'object',
            'required': ['@id', '@type'],
            'additionalProperties': False,
            'properties': {
                '@type': {'type': 'string'},
                '@id': {'type': ['integer', 'string']},
            }
        }

        share_schema = ShareV2Schema()

        for field_name in share_schema_type.explicit_fields:
            share_field = share_schema.get_field(share_schema_type.name, field_name)
            if share_field.is_required:
                schema['required'].append(share_field.name)
            schema['properties'][share_field.name] = self.json_schema_for_field(share_field)

        return JSONLDValidator.__json_schema_cache.setdefault(
            share_schema_type.name,
            schema,
        )

    def validator_for(self, share_schema_type):
        if share_schema_type.name in JSONLDValidator.__validator_cache:
            return JSONLDValidator.__validator_cache[share_schema_type.name]

        schema = self.json_schema_for_type(share_schema_type)

        return JSONLDValidator.__validator_cache.setdefault(
            share_schema_type.name,
            Draft4Validator(schema, format_checker=draft4_format_checker),
        )


def is_valid_iri(iri):
    # raises InvalidIRI if invalid
    IRILink().execute(iri)
    return True


draft4_format_checker.checks('uri', raises=InvalidIRI)(is_valid_iri)
