import os
import ujson

from jsonschema import validate


def is_valid_jsonld(value):
    module_path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(module_path, "jsonld-schema.json")) as file:
        schema = ujson.load(file)

    validate(value, schema)
