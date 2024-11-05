import base64
import dataclasses
import datetime
import json
import typing


def timestamp_to_readable_datetime(timestamp_in_milliseconds):
    milliseconds = int(timestamp_in_milliseconds)
    seconds = milliseconds / 1000
    return (
        datetime.datetime
        .fromtimestamp(seconds, tz=datetime.timezone.utc)
        .isoformat(timespec='minutes')
    )
