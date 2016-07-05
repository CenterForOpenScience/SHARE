import os
import ujson

import regex
from django.core.exceptions import ValidationError
from jsonschema import validate
# import rfc3987


def is_valid_jsonld(value):
    module_path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(module_path, "jsonld-schema.json")) as file:
        schema = ujson.load(file)

    validate(value, schema)

def is_valid_uri(value):
    # uri = rfc3987.get_compiled_pattern('^%(URI)s$')
    try:
        assert regex.match(r'.+//:[^/]/+.*', value)
        # assert uri.match(value)
        # assert not rfc3987.get_compiled_pattern('^%(relative_ref)s$').match('#f#g')
        # from unicodedata import lookup
        # smp = 'urn:' + lookup('OLD ITALIC LETTER A')  # U+00010300
        # assert not uri.match(smp)
        # m = rfc3987.get_compiled_pattern('^%(IRI)s$').match(smp)
    except BaseException as ex:
        raise ValidationError(ex)

