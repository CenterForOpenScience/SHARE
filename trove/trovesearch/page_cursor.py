from __future__ import annotations
import base64
import dataclasses
import enum
import json
import math
import typing

from trove.exceptions import InvalidPageCursorValue
from ._trovesearch_util import (
    VALUESEARCH_MAX,
    CARDSEARCH_MAX,
)

if typing.TYPE_CHECKING:
    from number import Number


__all__ = ('PageCursor', 'OffsetCursor', 'ReproduciblyRandomSampleCursor')


_MANY_MORE = math.inf


@dataclasses.dataclass
class PageCursor:
    page_size: Number
    total_count: Number = _MANY_MORE

    @staticmethod
    def from_queryparam_value(cursor_value: str) -> PageCursor:
        try:
            (_type_key, _args) = json.loads(base64.urlsafe_b64decode(cursor_value))
            _cls = _PageCursorTypes[_type_key].value
            assert issubclass(_cls, PageCursor)
            return _cls(*_args)
        except Exception:
            raise InvalidPageCursorValue(cursor_value)

    def as_queryparam_value(self) -> str:
        _as_json = json.dumps(dataclasses.astuple(self))
        _cursor_bytes = base64.urlsafe_b64encode(_as_json.encode())
        return _cursor_bytes.decode()

    def is_valid(self) -> bool:
        return self.page_size > 0 and (0 <= self.total_count <= _MANY_MORE)

    def has_many_more(self) -> bool:
        return self.total_count >= _MANY_MORE

    def next_cursor(self) -> typing.Self | None:
        return None

    def prev_cursor(self) -> typing.Self | None:
        return None

    def first_cursor(self) -> typing.Self | None:
        return None


@dataclasses.dataclass
class OffsetCursor(PageCursor):
    # page_size: Number (from PageCursor)
    # total_count: Number (from PageCursor)
    start_offset: Number = 0

    MAX_INDEX: typing.ClassVar[Number] = VALUESEARCH_MAX

    def is_valid(self) -> bool:
        return (
            super().is_valid()
            and 0 <= self.start_offset < self.max_index()
        )

    def is_first_page(self) -> bool:
        return self.start_offset == 0

    def max_index(self) -> Number:
        return (
            self.MAX_INDEX
            if self.has_many_more()
            else min(self.total_count or 0, self.MAX_INDEX)
        )

    def next_cursor(self):
        return dataclasses.replace(self, start_offset=(self.start_offset + self.page_size))

    def prev_cursor(self):
        return dataclasses.replace(self, start_offset=(self.start_offset - self.page_size))

    def first_cursor(self):
        return dataclasses.replace(self, start_offset=0)


@dataclasses.dataclass
class ReproduciblyRandomSampleCursor(OffsetCursor):
    # page_size: Number (from PageCursor)
    # total_count: Number (from PageCursor)
    # start_offset: Number (from OffsetCursor)
    first_page_ids: typing.Iterable[str] = ()

    MAX_INDEX: typing.ClassVar[Number] = CARDSEARCH_MAX

    def next_cursor(self):
        return (
            super().next_cursor()
            if self.first_page_ids
            else None
        )

    def prev_cursor(self):
        return (
            super().prev_cursor()
            if self.first_page_ids
            else None
        )


class _PageCursorTypes(enum.Enum):
    '''registry of cursor types into which cursor values can be deserialized'''
    PC = PageCursor
    OC = OffsetCursor
    RRSC = ReproduciblyRandomSampleCursor
