import zlib
import enum
import base64

from django.db import models
from django.core import exceptions


class Status(enum.IntEnum):
    PENDING = 0
    REJECTED = 1
    ACCEPTED = 2


class EnumField(models.Field):

    def __init__(self, enum, *args, **kwargs):
        self.__enum = enum
        super().__init__(*args, **kwargs)

    def db_type(self, connection):
        return 'integer'

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        return self.__enum(value)

    def to_python(self, value):
        if value is None or isinstance(value, EnumField):
            return value
        assert isinstance(value, self.__enum), '{!r} is not of type {}'.format(value, self.__enum)
        return value.value


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
        return zlib.decompress(base64.b64decode(value))
