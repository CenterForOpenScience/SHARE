import os
import json
import ujson
from collections import OrderedDict

from jsonschema import exceptions
from jsonschema import Draft4Validator, draft4_format_checker

from typedmodels.models import TypedModel

from django.db import connection
from django.apps import apps
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

from share.models.fields import ShareURLField
from share.transform.chain.links import IRILink
from share.transform.chain.exceptions import InvalidIRI


def is_valid_jsonld(value):
    raise Exception('Deprecated; use JSONLDValidator')


@deconstructible
class JSONLDValidator:

    __schema_cache = {}
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jsonld-schema.json')) as fobj:
        jsonld_schema = Draft4Validator(ujson.load(fobj))

    db_type_map = {
        'text': 'string',
        'boolean': 'boolean',
        'integer': 'integer',
        'varchar(254)': 'string',
        'timestamp with time zone': 'string',
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
                raise ValidationError('{} at /@graph/{}'.format(e.message, i, '/'.join(str(x) for x in e.path)))

        if refs['blank'] - nodes['blank']:
            raise ValidationError('Unresolved references {}'.format(json.dumps([
                OrderedDict([('@id', id), ('@type', type)]) for id, type in
                sorted(refs['blank'] - nodes['blank'])
            ])))

    def __eq__(self, other):
        return self.__check_existence == other.__check_existence

    def validate_node(self, value, refs, nodes):
        model = apps.app_configs['share'].models.get(value['@type'].lower())

        # concrete model is not valid for typed models
        if model is None or (issubclass(model, TypedModel) and model._meta.concrete_model is model):
            raise ValidationError("'{}' is not a valid type".format(value['@type']))

        self.validator_for(model).validate(value)

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

    def json_schema_for_field(self, field):
        if field.is_relation:
            if field.many_to_many:
                model = field.remote_field.through._meta.concrete_model
            else:
                model = field.related_model._meta.concrete_model

            if issubclass(model, TypedModel) and model._meta.concrete_model is model:
                allowed_models = model.get_type_classes()
            else:
                allowed_models = [model]

            rel = {
                'type': 'object',
                'description': getattr(field, 'description', ''),
                'required': ['@id', '@type'],
                'additionalProperties': False,
                'properties': {
                    '@id': {'type': ['string', 'integer']},
                    # Sorted so the same error message is sent back every time
                    '@type': {'enum': sorted(sum([
                        # Generate all acceptable variants of the class name
                        # Class, CLASS, class
                        [
                            m.__name__,
                            m.__name__.upper(),
                            m.__name__.lower(),
                        ] for m in allowed_models
                    ], []))},
                }
            }
            if field.many_to_many or field.one_to_many:
                return {'type': 'array', 'items': rel}
            return rel
        if field.choices:
            return {
                'enum': [c[1] for c in field.choices],
                'description': field.description
            }

        schema = {
            'type': JSONLDValidator.db_type_map[field.db_type(connection)],
            'description': field.description
        }
        if schema['type'] == 'string' and not field.blank:
            schema['minLength'] = 1
        if isinstance(field, ShareURLField):
            schema['format'] = 'uri'

        return schema

    def validator_for(self, model):
        if model in JSONLDValidator.__schema_cache:
            return JSONLDValidator.__schema_cache[model]

        schema = {
            'type': 'object',
            'required': ['@id', '@type'],
            'additionalProperties': False,
            'properties': {
                'extra': {'type': 'object'},
                '@type': {'type': 'string'},
                '@id': {'type': ['integer', 'string']},
            }
        }

        for field in self.allowed_fields_for_model(model):
            if not (field.null or field.blank or field.many_to_many or field.one_to_many or field.has_default()):
                schema['required'].append(field.name)
            schema['properties'][field.name] = self.json_schema_for_field(field)

        return JSONLDValidator.__schema_cache.setdefault(model, Draft4Validator(schema, format_checker=draft4_format_checker))

    def allowed_fields_for_model(self, model):
        excluded = {'id', 'type', 'sources', 'changes', 'same_as', 'extra'}
        fields = model._meta.get_fields()
        allowed_fields = [f for f in fields if f.editable and f.name not in excluded]
        # Include one-to-many relations to models with no other relations
        allowed_fields.extend(f for f in fields if f.one_to_many and f.name not in excluded and hasattr(f.related_model, 'VersionModel') and not [rf for rf in f.related_model._meta.get_fields() if rf.editable and rf.is_relation and rf.remote_field != f and rf.name not in excluded])
        return allowed_fields


def is_valid_iri(iri):
    try:
        IRILink().execute(iri)
    except InvalidIRI:
        return False
    return True


draft4_format_checker.checks('uri', raises=ValueError)(is_valid_iri)
