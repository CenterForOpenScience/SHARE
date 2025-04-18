import datetime
import re


def fromisoformat(date_str: str) -> datetime.datetime:
    # wrapper around `datetime.datetime.fromisoformat` that supports "Z" UTC suffix
    # (may be removed in python 3.11+, when `fromisoformat` handles more iso-6801 formats)
    return datetime.datetime.fromisoformat(
        re.sub('Z$', '+00:00', date_str),  # replace "Z" shorthand with explicit timezone offset
    )
