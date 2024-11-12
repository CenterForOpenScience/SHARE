from __future__ import annotations
import base64
import dataclasses
import enum
import json
import typing

from trove.exceptions import InvalidPageCursorValue


__all__ = ('PageCursor', 'OffsetCursor', 'ReproduciblyRandomSampleCursor')


MANY_MORE = -1
MAX_OFFSET = 9997


@dataclasses.dataclass
class PageCursor:
    page_size: int
    total_count: int = MANY_MORE

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
    # page_size: int (from PageCursor)
    # total_count: int (from PageCursor)
    start_offset: int = 0

    def is_valid(self) -> bool:
        return (
            super().is_valid()
            and 0 <= self.start_offset <= MAX_OFFSET
            and (
                self.total_count == MANY_MORE
                or self.start_offset < self.total_count
            )
        )

    def is_first_page(self) -> bool:
        return self.start_offset == 0

    def next_cursor(self):
        _next = dataclasses.replace(self, start_offset=(self.start_offset + self.page_size))
        return (_next if _next.is_valid() else None)

    def prev_cursor(self):
        _prev = dataclasses.replace(self, start_offset=(self.start_offset - self.page_size))
        return (_prev if _prev.is_valid() else None)

    def first_cursor(self):
        _first = dataclasses.replace(self, start_offset=0)
        return (_first if _first.is_valid() else None)


@dataclasses.dataclass
class ReproduciblyRandomSampleCursor(OffsetCursor):
    # page_size: int (from PageCursor)
    # total_count: int (from PageCursor)
    # start_offset: int (from OffsetCursor)
    first_page_ids: list[str] = dataclasses.field(default_factory=list)

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
