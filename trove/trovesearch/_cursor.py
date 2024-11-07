from __future__ import annotations
import base64
import dataclasses
import json
import typing

from ._trovesearch_util import (
    VALUESEARCH_MAX,
    CARDSEARCH_MAX,
)

if typing.TYPE_CHECKING:
    from trove.trovesearch.search_params import (
        CardsearchParams,
        PageParam,
    )

__all__ = ('BasicCursor', 'OffsetCursor', 'CardsearchCursor')

_MANY_MORE = -1  # special count value

_SomeDataclass = typing.TypeVar('_SomeDataclass')


@dataclasses.dataclass
class BasicCursor:
    sample_size: int

    def as_queryparam_value(self) -> str:
        _as_json = json.dumps(dataclasses.astuple(self))
        _cursor_bytes = base64.urlsafe_b64encode(_as_json.encode())
        return _cursor_bytes.decode()

    @classmethod
    def from_queryparam_value(cls, cursor_value: str):
        _as_list = json.loads(base64.urlsafe_b64decode(cursor_value))
        return cls(*_as_list)

    @classmethod
    def from_page_param(cls, page: PageParam) -> BasicCursor:
        if page.cursor:
            return cls.from_queryparam_value(page.cursor)
        assert page.size is not None
        return cls(sample_size=page.size)

    def next_cursor(self) -> typing.Self | None:
        return None

    def prev_cursor(self) -> typing.Self | None:
        return None

    def first_cursor(self) -> typing.Self | None:
        return None


@dataclasses.dataclass
class OffsetCursor(BasicCursor):
    start_index: int = 0
    result_count: int = _MANY_MORE

    MAX_INDEX: typing.ClassVar[int] = VALUESEARCH_MAX

    def next_cursor(self) -> typing.Self | None:
        _next = dataclasses.replace(self, start_index=(self.start_index + self.sample_size))
        return (_next if _next.is_valid_cursor() else None)

    def prev_cursor(self) -> typing.Self | None:
        _prev = dataclasses.replace(self, start_index=(self.start_index - self.sample_size))
        return (_prev if _prev.is_valid_cursor() else None)

    def first_cursor(self) -> typing.Self | None:
        if self.is_first_page():
            return None
        return dataclasses.replace(self, start_index=0)

    def is_first_page(self) -> bool:
        return self.start_index == 0

    def has_many_more(self) -> bool:
        return self.result_count == -1

    def max_index(self) -> int:
        return (
            self.MAX_INDEX
            if self.has_many_more()
            else min(self.result_count or 0, self.MAX_INDEX)
        )

    def is_valid_cursor(self) -> bool:
        return 0 <= self.start_index < self.max_index()


@dataclasses.dataclass
class CardsearchCursor(OffsetCursor):
    random_sort: bool = True  # how to sort by relevance to nothingness? randomness!
    first_page_ids: tuple[str, ...] = ()

    MAX_INDEX: typing.ClassVar[int] = CARDSEARCH_MAX

    @classmethod
    def from_cardsearch_params(cls, params: CardsearchParams) -> CardsearchCursor:
        if params.page.cursor:
            return cls.from_queryparam_value(params.page.cursor)
        assert params.page.size is not None
        return cls(
            sample_size=params.page.size,
            random_sort=(
                not params.sort_list
                and not params.cardsearch_textsegment_set
            ),
            start_index=0,
        )

    def cardsearch_start_index(self) -> int:
        if self.is_first_page() or not self.random_sort:
            return self.start_index
        return self.start_index - len(self.first_page_ids)

    def first_cursor(self) -> typing.Self | None:
        if self.random_sort and not self.first_page_ids:
            return None
        return super().first_cursor()

    def prev_cursor(self) -> typing.Self | None:
        if self.random_sort and not self.first_page_ids:
            return None
        return super().prev_cursor()

