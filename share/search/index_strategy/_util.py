import base64
import dataclasses
import datetime
import json


def timestamp_to_readable_datetime(timestamp_in_milliseconds):
    milliseconds = int(timestamp_in_milliseconds)
    seconds = milliseconds / 1000
    return (
        datetime.datetime
        .fromtimestamp(seconds, tz=datetime.timezone.utc)
        .isoformat(timespec='minutes')
    )


def encode_cursor_dataclass(dataclass_instance) -> str:
    _as_json = json.dumps(dataclasses.astuple(dataclass_instance))
    _cursor_bytes = base64.b64encode(_as_json.encode())
    return _cursor_bytes.decode()


def decode_cursor_dataclass(cursor: str, dataclass_class) -> dict:
    _as_list = json.loads(base64.b64decode(cursor))
    return dataclass_class(*_as_list)
