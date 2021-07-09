import datetime as dt
import json
from decimal import Decimal
from functools import partial

from dateutil import parser
import jwe
from psycopg2.extras import Json

from django import forms
from django.conf import settings
from django.contrib.postgres import lookups
from django.contrib.postgres.fields.jsonb import JSONField
from django.core import validators
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import ugettext_lazy as _


class DateTimeAwareJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, dt.datetime):
            return dict(type='encoded_datetime', value=o.isoformat())
        elif isinstance(o, dt.date):
            return dict(type='encoded_date', value=o.isoformat())
        elif isinstance(o, dt.time):
            return dict(type='encoded_time', value=o.isoformat())
        elif isinstance(o, Decimal):
            return dict(type='encoded_decimal', value=str(o))
        return super(DateTimeAwareJSONEncoder, self).default(o)


def decode_datetime_objects(nested_value):
    if isinstance(nested_value, list):
        return [decode_datetime_objects(item) for item in nested_value]
    elif isinstance(nested_value, dict):
        for key, value in nested_value.items():
            if isinstance(value, dict) and 'type' in value.keys():
                if value['type'] == 'encoded_datetime':
                    nested_value[key] = parser.parse(value['value'])
                if value['type'] == 'encoded_date':
                    nested_value[key] = parser.parse(value['value']).date()
                if value['type'] == 'encoded_time':
                    nested_value[key] = parser.parse(value['value']).time()
                if value['type'] == 'encoded_decimal':
                    nested_value[key] = Decimal(value['value'])
            elif isinstance(value, dict):
                nested_value[key] = decode_datetime_objects(value)
            elif isinstance(value, list):
                nested_value[key] = decode_datetime_objects(value)
        return nested_value
    return nested_value


class DateTimeAwareJSONField(JSONField):
    def get_prep_value(self, value):
        if value is not None:
            return Json(value, dumps=partial(json.dumps, cls=DateTimeAwareJSONEncoder))
        return value

    def to_python(self, value):
        if value is None:
            return None
        return super(DateTimeAwareJSONField, self).to_python(decode_datetime_objects(value))

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type in ('has_key', 'has_keys', 'has_any_keys'):
            return value
        if isinstance(value, (dict, list)):
            return Json(value, dumps=partial(json.dumps, cls=DateTimeAwareJSONEncoder))
        return super(JSONField, self).get_prep_lookup(lookup_type, value)

    def validate(self, value, model_instance):
        super(JSONField, self).validate(value, model_instance)
        try:
            json.dumps(value, cls=DateTimeAwareJSONEncoder)
        except TypeError:
            raise ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )


JSONField.register_lookup(lookups.DataContains)
JSONField.register_lookup(lookups.ContainedBy)
JSONField.register_lookup(lookups.HasKey)
JSONField.register_lookup(lookups.HasKeys)
JSONField.register_lookup(lookups.HasAnyKeys)


# stub left just for migrations
class TypedManyToManyField(models.ManyToManyField):
    pass


class ShareURLField(models.TextField):
    default_validators = [validators.URLValidator()]
    description = _("URL")

    def __init__(self, verbose_name=None, name=None, **kwargs):
        super(ShareURLField, self).__init__(verbose_name, name, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(ShareURLField, self).deconstruct()
        kwargs.pop('max_length', None)
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        # As with CharField, this will cause URL validation to be performed
        # twice.
        defaults = {
            'form_class': forms.URLField,
        }
        if self.null and self.unique:
            defaults['empty_value'] = None
        defaults.update(kwargs)
        return super(ShareURLField, self).formfield(**defaults)


class EncryptedJSONField(models.BinaryField):
    """
    This field transparently encrypts data in the database. It should probably only be used with PG unless
    the user takes into account the db specific trade-offs with TextFields.
    """
    prefix = b'jwe:::'

    def get_db_prep_value(self, input_json, **kwargs):
        if not input_json:
            return None

        input_json = self.prefix + jwe.encrypt(json.dumps(input_json).encode('utf-8'), settings.SENSITIVE_DATA_KEY)

        return input_json

    def to_python(self, output_json):
        if not output_json:
            return None

        output_json = json.loads(jwe.decrypt(bytes(output_json[len(self.prefix):]), settings.SENSITIVE_DATA_KEY).decode('utf-8'))

        return output_json

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)
