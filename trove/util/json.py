from __future__ import annotations
from collections.abc import (
    Iterable,
    Sequence,
    Generator,
)
import datetime


###
# types for json-serializable stuff

JsonPrimitive = str | int | float | bool | None

type JsonValue = JsonPrimitive | list[JsonValue] | JsonObject

type JsonNonArrayValue = JsonPrimitive | JsonObject

type JsonObject = dict[str, JsonValue]

type JsonPath = Sequence[str]  # path of json keys

JSONLD_VALUE_KEYS = ('@value', '@id')

###
# utils for navigating nested json in the style of trove.derive.osfmap_json
# (TODO: more general json-ld utils)


def json_vals(json_obj: JsonObject, path: JsonPath) -> Generator[JsonValue]:
    assert path
    (_step, *_rest) = path
    try:
        _val = json_obj[_step]
    except KeyError:
        return
    if _rest:
        if isinstance(_val, dict):
            yield from json_vals(_val, _rest)
        elif isinstance(_val, list):
            for _val_obj in _val:
                if isinstance(_val_obj, dict):
                    yield from json_vals(_val_obj, _rest)
    else:
        if isinstance(_val, list):
            yield from _val
        else:
            yield _val


def json_prims(
    json_val: JsonValue,
    path: JsonPath,
    value_key_options: Iterable[str] = JSONLD_VALUE_KEYS,
) -> Generator[JsonPrimitive]:
    if isinstance(json_val, list):
        for _list_val in json_val:
            yield from json_prims(_list_val, path, value_key_options)
    elif path:
        if isinstance(json_val, dict):
            for _path_val in json_vals(json_val, path):
                yield from json_prims(_path_val, (), value_key_options)
    else:  # no path; not list
        if isinstance(json_val, JsonPrimitive):
            yield json_val
        elif isinstance(json_val, dict):
            try:
                yield next(
                    _val
                    for _key in value_key_options
                    if _key in json_val and isinstance(_val := json_val[_key], JsonPrimitive)
                )
            except StopIteration:
                pass


def json_strs(
    json_val: JsonValue,
    path: JsonPath,
    value_key_options: Iterable[str] = JSONLD_VALUE_KEYS,
    coerce_str: bool = False,
) -> Generator[str]:
    for _prim in json_prims(json_val, path, value_key_options):
        if isinstance(_prim, str):
            yield _prim
        elif coerce_str and (_prim is not None):
            yield str(_prim)


def json_datetimes(
    json_val: JsonValue,
    path: JsonPath,
) -> Generator[datetime.datetime]:
    for _prim in json_prims(json_val, path):
        if isinstance(_prim, str):
            try:
                yield datetime.datetime.fromisoformat(_prim)
            except ValueError:
                pass
