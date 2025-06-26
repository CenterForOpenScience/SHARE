from __future__ import annotations
import base64
import dataclasses
import enum
import json
import math
import typing

from trove.exceptions import InvalidPageCursorValue
from typing import Any

__all__ = ('PageCursor', 'OffsetCursor', 'ReproduciblyRandomSampleCursor')


MANY_MORE = math.inf
MAX_OFFSET = 9997

DEFAULT_PAGE_SIZE = 13
MAX_PAGE_SIZE = 101
UNBOUNDED_PAGE_SIZE = math.inf  # json-serialized as "Infinity"


@dataclasses.dataclass
class PageCursor:
    page_size: int | float = DEFAULT_PAGE_SIZE
    total_count: int | float = MANY_MORE

    @classmethod
    def from_queryparam_value(cls, cursor_value: str) -> typing.Self:
        try:
            (_type_key, *_args) = json.loads(base64.urlsafe_b64decode(cursor_value))
            _cls = _PageCursorTypes[_type_key].value
            assert issubclass(_cls, cls)
            return _cls(*_args)
        except Exception:
            raise InvalidPageCursorValue(cursor_value)

    @classmethod
    def from_cursor(cls, other_cursor: PageCursor) -> typing.Self:
        if isinstance(other_cursor, cls):
            return dataclasses.replace(other_cursor)  # simple copy
        return cls(*dataclasses.astuple(other_cursor))

    @property
    def bounded_page_size(self) -> int:
        return (
            MAX_PAGE_SIZE
            if self.page_size > MAX_PAGE_SIZE
            else int(self.page_size)
        )

    @property
    def is_complete_page(self) -> bool:
        return self.bounded_page_size == self.page_size

    def as_queryparam_value(self) -> str:
        _cls_key = _PageCursorTypes(type(self)).name
        _as_json = json.dumps([_cls_key, *dataclasses.astuple(self)])
        _cursor_bytes = base64.urlsafe_b64encode(_as_json.encode())
        return _cursor_bytes.decode()

    def is_basic(self) -> bool:
        return type(self) is PageCursor

    def is_valid(self) -> bool:
        return self.page_size > 0 and (
            self.total_count == MANY_MORE or self.total_count >= 0
        )

    def has_many_more(self) -> bool:
        return self.total_count == MANY_MORE

    def next_cursor(self) -> typing.Self | None:
        return None

    def prev_cursor(self) -> typing.Self | None:
        return None

    def first_cursor(self) -> typing.Self | None:
        return None


@dataclasses.dataclass
class OffsetCursor(PageCursor):
    # page_size: int | float (from PageCursor)
    # total_count: int | float (from PageCursor)
    start_offset: int = 0

    @property
    def bounded_page_size(self) -> int:
        # overrides PageCursor
        _bounded_page_size = super().bounded_page_size
        if (_bounded_page_size < self.page_size < MAX_OFFSET):
            _remaining = self.page_size - self.start_offset
            _bounded_page_size = int(min(_bounded_page_size, _remaining))
        return _bounded_page_size

    def is_valid(self) -> bool:
        _end_offset = (
            self.total_count
            if self.is_complete_page
            else min(self.total_count, self.page_size)
        )
        return (
            super().is_valid()
            and 0 <= self.start_offset <= MAX_OFFSET
            and self.start_offset < _end_offset
        )

    def is_first_page(self) -> bool:
        return self.start_offset == 0

    def next_cursor(self) -> OffsetCursor | None:
        _next = dataclasses.replace(self, start_offset=int(self.start_offset + self.bounded_page_size))
        return _next if _next.is_valid() else None

    def prev_cursor(self) -> OffsetCursor | None:
        _prev = dataclasses.replace(self, start_offset=int(self.start_offset - self.bounded_page_size))
        return _prev if _prev.is_valid() else None

    def first_cursor(self) -> OffsetCursor | None:
        _first = dataclasses.replace(self, start_offset=0)
        return _first if _first.is_valid() else None


@dataclasses.dataclass
class ReproduciblyRandomSampleCursor(OffsetCursor):
    # page_size: int (from PageCursor)
    # total_count: int (from PageCursor)
    # start_offset: int (from OffsetCursor)
    first_page_ids: list[str] = dataclasses.field(default_factory=list)

    def next_cursor(self) -> ReproduciblyRandomSampleCursor | None:
        return (
            super().next_cursor()  # type: ignore
            if self.first_page_ids
            else None
        )

    def prev_cursor(self) -> ReproduciblyRandomSampleCursor | None:
        return (
            super().prev_cursor()  # type: ignore
            if self.first_page_ids
            else None
        )


@dataclasses.dataclass
class SearchAfterCursor(PageCursor):
    # page_size: int (from PageCursor)
    # total_count: int (from PageCursor)
    search_after: list[Any] | None = None
    next_search_after: list[Any] | None = None
    prev_search_after: list[Any] | None = None

    def is_first_page(self) -> bool:
        return self.search_after is None

    def next_cursor(self) -> SearchAfterCursor | None:
        _next = dataclasses.replace(
            self,
            search_after=self.next_search_after,
            next_search_after=None,
        )
        return _next if _next.is_valid() else None

    def prev_cursor(self) -> SearchAfterCursor | None:
        _prev = dataclasses.replace(
            self,
            search_after=self.prev_search_after,
            next_search_after=self.search_after,
        )
        return _prev if _prev.is_valid() else None

    def first_cursor(self) -> SearchAfterCursor | None:
        _first = dataclasses.replace(
            self,
            search_after=None,
            next_search_after=None,
            prev_search_after=None,
        )
        return _first if _first.is_valid() else None


class _PageCursorTypes(enum.Enum):
    '''registry of cursor types into which cursor values can be deserialized'''
    PC = PageCursor
    OC = OffsetCursor
    RRSC = ReproduciblyRandomSampleCursor
    SAC = SearchAfterCursor
