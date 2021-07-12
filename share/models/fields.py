import datetime as dt
import json
from decimal import Decimal

from dateutil import parser
import jwe

from django import forms
from django.conf import settings
from django.core import validators
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy as _


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
        return super().default(o)


def decode_datetime_object(json_object):
    if set(json_object.keys()) == {'type', 'value'}:
        if json_object['type'] == 'encoded_datetime':
            return parser.parse(json_object['value'])
        if json_object['type'] == 'encoded_date':
            return parser.parse(json_object['value']).date()
        if json_object['type'] == 'encoded_time':
            return parser.parse(json_object['value']).time()
        if json_object['type'] == 'encoded_decimal':
            return Decimal(json_object['value'])
    return json_object


class DateTimeAwareJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, object_hook=None, **kwargs):
        return super().__init__(
            *args,
            **kwargs,
            object_hook=decode_datetime_object,
        )


class DateTimeAwareJSONField(models.JSONField):
    def __init__(self, *args, encoder=None, decoder=None, **kwargs):
        return super().__init__(
            *args,
            **kwargs,
            encoder=DateTimeAwareJSONEncoder,
            decoder=DateTimeAwareJSONDecoder,
        )


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
