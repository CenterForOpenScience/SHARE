import os
import ujson

from django.core.exceptions import ValidationError
from jsonschema import validate


def is_valid_jsonld(value):
    try:
        json_value = ujson.loads(value)
    except:
        raise ValidationError(message='Enter valid JSON.', code='invalid')

    module_path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(module_path, "jsonld-schema.json")) as file:
        schema = ujson.load(file)

    validate(json_value, schema)
