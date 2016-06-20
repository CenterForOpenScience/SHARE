import zlib
import base64
import binascii
import ujson
import os

from django.core.exceptions import ValidationError
from django.db import models
from django.core import exceptions
from django.contrib.postgres.fields.jsonb import JSONField
from django.contrib.postgres import lookups
from psycopg2.extras import Json
from django.utils.translation import ugettext_lazy as _
from jsonschema import validate


class ZipField(models.Field):

    def db_type(self, connection):
        return 'bytea'

    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname)
        assert isinstance(value, (bytes, str)), 'Values must be of type str or bytes, got {}'.format(type(value))
        if not value and not self.blank:
            raise exceptions.ValidationError('"{}" on {!r} can not be blank or empty'.format(self.attname, model_instance))
        if isinstance(value, str):
            value = value.encode()
        return base64.b64encode(zlib.compress(value))

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        assert value
        return zlib.decompress(base64.b64decode(value))

    def to_python(self, value):
        assert value
        if value is None or isinstance(value, ZipField):
            return value
        try:
            base64.decodebytes(bytes(value, 'utf8'))
        except binascii.Error:
            # it's not base64, return it.
            return value

        return zlib.decompress(base64.b64decode(value))


class DatetimeAwareJSONField(JSONField):
    def get_prep_value(self, value):
        if value is not None:
            return Json(value, dumps=ujson.dumps)
        return value

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type in ('has_key', 'has_keys', 'has_any_keys'):
            return value
        if isinstance(value, (dict, list)):
            return Json(value, dumps=ujson.dumps)
        return super(JSONField, self).get_prep_lookup(lookup_type, value)

    def validate(self, value, model_instance):
        super(JSONField, self).validate(value, model_instance)
        try:
            ujson.dumps(value)
        except TypeError:
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )


JSONField.register_lookup(lookups.DataContains)
JSONField.register_lookup(lookups.ContainedBy)
JSONField.register_lookup(lookups.HasKey)
JSONField.register_lookup(lookups.HasKeys)
JSONField.register_lookup(lookups.HasAnyKeys)


class JSONValidator(object):
    message = _('Enter valid JSON.')
    code = 'invalid'

    def __call__(self, value):
        try:
            ujson.loads(value)
            return
        except:
            raise ValidationError(message=self.message, code=self.code)


class JSONLDValidator(JSONValidator):
    message = _('Enter valid JSON-LD.')
    code = 'invalid'

    def __call__(self, value):
        # check if it's json
        super(JSONLDValidator, self).__call__(value)

        module_path = os.path.dirname(os.path.abspath(__file__))
        schema = ujson.load(os.path.join(module_path, 'jsonld-schema.json'))

        # this will raise a validation error.
        validate(value, schema)
