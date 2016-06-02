import json
import copy
import datetime
import time


def infer_jsonschema(d, hints=None):
    if not hints:
        hints = {}
    def _field(d, keys=None):
        keys = [] if not keys else keys
        schema_field = {
        }
        for key, value in d.items():
            schema_field[key] = {}
            if isinstance(value, str):
                schema_field[key]["type"] = "string"
            elif isinstance(value, bool):
                schema_field[key]["type"] = "boolean"
            elif isinstance(value, dict):
                schema_field[key]["type"] = "object"
                schema_field[key]["properties"] = _field(value, keys + [key])
            elif isinstance(value, list):
                schema_field[key]["type"] = "array"
                # wrapping this in items allows it traverse dicts or not in the for loop
                schema_field[key].update(_field({"items": value[0]}, keys + [key]))
            elif isinstance(value, datetime.datetime) or isinstance(value, time.struct_time):
                schema_field[key]["type"] = "string"
                schema_field[key]["format"] = "date-time"
            elif value == None:
                schema_field[key]["oneOf"] = [
                    {"type": "string"},
                    {"type": "null"}
                ]
                print('.'.join(keys + [key]), 'is None')
            else:
                print('.'.join(keys + [key]), 'is unrecognized')
                schema_field[key]["type"] = "string"

        return schema_field

    schema = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "properties": _field(d)
    }

    for key, value in hints.items():
        if value == "date-time":
            del schema["properties"][key]
            schema["properties"][key] = {}
            schema["properties"][key]["type"] = "string"
            schema["properties"][key]["format"] = "date-time"

    return schema
