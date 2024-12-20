from __future__ import annotations
import dataclasses
import functools
from typing import (
    Generator,
    Iterable,
    Optional,
    TYPE_CHECKING,
)

from primitive_metadata import primitive_rdf

from trove.trovesearch.page_cursor import (
    PageCursor,
    ReproduciblyRandomSampleCursor,
)
from trove.trovesearch.search_params import (
    BaseTroveParams,
    CardsearchParams,
    ValuesearchParams,
)
from trove.vocab.namespaces import TROVE
from trove.vocab.trove import trove_indexcard_namespace

if TYPE_CHECKING:
    from share.search.index_strategy import IndexStrategy


@dataclasses.dataclass
class BasicSearchHandle:
    cursor: PageCursor
    index_strategy: IndexStrategy | None  # TODO: make the handle the one that knows how to use the strategy
    search_params: BaseTroveParams

    @property
    def total_result_count(self) -> primitive_rdf.Literal:
        return (
            TROVE['ten-thousands-and-more']
            if self.cursor.has_many_more()
            else self.cursor.total_count
        )

    @functools.cached_property
    def search_result_page(self) -> Iterable | None:
        ...

    def iter_all_pages(self) -> Generator:
        _handle: BasicSearchHandle | None = self
        while _handle is not None:
            yield from _handle.search_result_page
            _handle = _handle.get_next()

    def get_next(self) -> BasicSearchHandle | None:
        _next_cursor = self.cursor.next_cursor()
        return (
            None
            if _next_cursor is None
            else dataclasses.replace(
                self,
                cursor=_next_cursor,
                **self._next_replace_kwargs(),
            )
        )

    def _next_replace_kwargs(self) -> dict:
        return {
            'cursor': self.cursor.next_cursor(),
            'search_result_page': None,
        }


@dataclasses.dataclass
class CardsearchHandle(BasicSearchHandle):
    related_propertypath_results: list[PropertypathUsage]
    cardsearch_params: CardsearchParams

    def __post_init__(self):
        _cursor = self.cursor
        _page = self.search_result_page
        if (  # TODO: move this logic into the... cursor?
            isinstance(_cursor, ReproduciblyRandomSampleCursor)
            and _cursor.is_first_page()
            and _page is not None
        ):
            if _cursor.first_page_ids:
                # revisiting first page; reproduce original random order
                _ordering_by_id = {
                    _id: _i
                    for (_i, _id) in enumerate(_cursor.first_page_ids)
                }
                self.search_result_page = sorted(
                    _page,
                    key=lambda _r: _ordering_by_id[_r.card_id],
                )
            elif not _cursor.has_many_more():
                # visiting first page for the first time
                _cursor.first_page_ids = [_result.card_id for _result in _page]
        return _page

    def _next_replace_kwargs(self) -> dict:
        _next_kwargs = super()._next_replace_kwargs()
        return {
            **_next_kwargs,
            'related_propertypath_results': [],
            'cardsearch_params': dataclasses.replace(
                self.cardsearch_params,
                page_cursor=_next_kwargs['cursor'],
            ),
        }


@dataclasses.dataclass
class ValuesearchHandle(BasicSearchHandle):
    valuesearch_params: ValuesearchParams


@dataclasses.dataclass
class TextMatchEvidence:
    property_path: tuple[str, ...]
    matching_highlight: primitive_rdf.Literal
    card_iri: Optional[str]  # may be left implicit


@dataclasses.dataclass
class CardsearchResult:
    text_match_evidence: list[TextMatchEvidence]
    card_iri: str
    card_pk: str = ''

    @property
    def card_uuid(self):
        # card iri has the uuid at the end
        return primitive_rdf.iri_minus_namespace(
            self.card_iri,
            namespace=trove_indexcard_namespace(),
        )

    @property
    def card_id(self):
        return self.card_pk or self.card_uuid


@dataclasses.dataclass
class PropertypathUsage:
    property_path: tuple[str, ...]
    usage_count: int


@dataclasses.dataclass
class ValuesearchResult:
    value_iri: str | None
    value_value: str | None = None
    value_type: Iterable[str] = ()
    name_text: Iterable[str] = ()
    title_text: Iterable[str] = ()
    label_text: Iterable[str] = ()
    match_count: int = 0
    total_count: int = 0

    def __post_init__(self):
        assert (self.value_iri is not None) or (self.value_value is not None), (
            f'either value_iri or value_value required (on {self})'
        )


###
# local helpers

def _cursor_value(cursor: PageCursor | None) -> str:
    return (
        cursor.as_queryparam_value()
        if cursor is not None and cursor.is_valid()
        else ''
    )
