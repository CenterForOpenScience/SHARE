import json

from cryptography.exceptions import InvalidTag
from django.db import models
from django.conf import settings
import jwe

SENSITIVE_DATA_KEY = jwe.kdf(settings.SECRET_KEY.encode('utf-8'), settings.SALT.encode('utf-8'))


class EncryptedJSONField(models.BinaryField):
    '''
    This field transparently encrypts data in the database. It should probably only be used with PG unless
    the user takes into account the db specific trade-offs with TextFields.
    '''
    prefix = 'jwe:::'

    def get_db_prep_value(self, input_json, **kwargs):
        if input_json:
            input_json = json.dumps(input_json).encode('utf-8')
            try:
                input_json = self.prefix.encode('utf-8') + jwe.encrypt(bytes(input_json), SENSITIVE_DATA_KEY)
            except InvalidTag:
                # Allow use of an encrypted DB locally without encrypting fields
                if settings.DEBUG_MODE:
                    pass
                else:
                    raise
        return input_json

    def to_python(self, output_json):
        if output_json:
            try:
                output_json = jwe.decrypt(bytes(output_json[len(self.prefix.encode('utf-8')):]), SENSITIVE_DATA_KEY)
            except InvalidTag:
                # Allow use of an encrypted DB locally without decrypting fields
                if settings.DEBUG_MODE:
                    pass
                else:
                    raise
            output_json = json.loads(output_json.decode("utf-8"))
        return output_json

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)
