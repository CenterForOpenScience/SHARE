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


def path_as_keyword(path: tuple[str]) -> str:
    assert isinstance(path, (list, tuple)) and all(
        isinstance(_pathstep, str)
        for _pathstep in path
    ), f'expected list or tuple of str, got {path}'
    return json.dumps(path)
