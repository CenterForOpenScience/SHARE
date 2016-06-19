import zlib
import base64

import binascii
from django.db import models
from django.core import exceptions


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
        # TODO: Not sure if this is necessary or just solving a temporary error
        try:
            base64.decodestring(bytes(value, 'utf8'))
        except binascii.Error:
            value = base64.b64encode(zlib.compress(bytes(value, 'utf8')))
        # END TODO
        return zlib.decompress(base64.b64decode(value))
