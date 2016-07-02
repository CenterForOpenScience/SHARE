import binascii
import zlib

import ujson
from django.contrib.postgres import lookups
from django.contrib.postgres.fields.jsonb import JSONField
from django.core import exceptions
from django.db import models
from psycopg2.extras import Json


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
        return zlib.compress(value)

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        assert value
        return zlib.decompress(value)

    def to_python(self, value):
        assert value
        if value is None or isinstance(value, ZipField):
            return value
        try:
            bytes(value, 'utf8')
        except binascii.Error:
            # it's not base64, return it.
            return value

        return zlib.decompress(value)


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


class ShareOneToOneField(models.OneToOneField):
    def __init__(self, model, **kwargs):
        self.__kwargs = kwargs
        super().__init__(model, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        actual = self.__class__.mro()[1](self.remote_field.model, **self.__kwargs)
        actual.contribute_to_class(cls, name, **kwargs)

        if isinstance(self.remote_field.model, str):
            version = self.__class__.mro()[1](self.remote_field.model + 'Version', **{**self.__kwargs, 'editable': True})
        else:
            version = self.__class__.mro()[1](self.remote_field.model.VersionModel, **{**self.__kwargs, 'editable': True})

        version.contribute_to_class(cls, name + '_version', **kwargs)

        actual._share_version_field = version


class ShareForeignKey(models.ForeignKey):

    def __init__(self, model, **kwargs):
        self.__kwargs = kwargs
        super().__init__(model, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        actual = self.__class__.mro()[1](self.remote_field.model, **self.__kwargs)
        actual.contribute_to_class(cls, name, **kwargs)

        if isinstance(self.remote_field.model, str):
            version = self.__class__.mro()[1](self.remote_field.model + 'Version', **{**self.__kwargs, 'editable': True})
        else:
            version = self.__class__.mro()[1](self.remote_field.model.VersionModel, **{**self.__kwargs, 'editable': True})

        version.contribute_to_class(cls, name + '_version', **kwargs)

        actual._share_version_field = version


class ShareManyToManyField(models.ManyToManyField):

    def __init__(self, model, **kwargs):
        self.__kwargs = kwargs
        super().__init__(model, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        actual = self.__class__.mro()[1](self.remote_field.model, **self.__kwargs)
        actual.contribute_to_class(cls, name, **kwargs)
        if isinstance(self.remote_field.model, str):
            version = self.__class__.mro()[1](self.remote_field.model + 'Version', **{**self.__kwargs, 'editable': True})
        else:
            version = self.__class__.mro()[1](self.remote_field.model.VersionModel, **{**self.__kwargs, 'editable': True})
        version.contribute_to_class(cls, name[:-1] + '_versions', **kwargs)

        actual._share_version_field = version
