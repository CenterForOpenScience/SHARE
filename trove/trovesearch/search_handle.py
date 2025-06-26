from __future__ import annotations
import dataclasses
import typing

from primitive_metadata import primitive_rdf

from trove.trovesearch.page_cursor import (
    PageCursor,
    ReproduciblyRandomSampleCursor,
)
from trove.trovesearch.search_params import (
    CardsearchParams,
)
from trove.util.trove_params import BasicTroveParams
from trove.vocab.namespaces import TROVE
from trove.vocab.trove import trove_indexcard_namespace


@dataclasses.dataclass
class BasicSearchHandle:
    cursor: PageCursor
    search_params: BasicTroveParams
    handler: typing.Callable[[BasicTroveParams], typing.Self] | None = None

    @property
    def total_result_count(self) -> primitive_rdf.Literal:
        return (
            TROVE['ten-thousands-and-more']
            if self.cursor.has_many_more()
            else self.cursor.total_count
        )

    def get_next_streaming_handle(self) -> typing.Self | None:
        raise NotImplementedError


@dataclasses.dataclass
class CardsearchHandle(BasicSearchHandle):
    search_result_page: typing.Iterable[CardsearchResult] = ()
    related_propertypath_results: list[PropertypathUsage] = dataclasses.field(default_factory=list)

    def __post_init__(self):  # type: ignore
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

    def get_next_streaming_handle(self) -> typing.Self | None:
        if self.cursor.is_complete_page:
            return None
        _next_cursor = self.cursor.next_cursor()
        if (_next_cursor is not None) and (self.handler is not None):
            assert isinstance(self.search_params, CardsearchParams)
            _next_params = dataclasses.replace(
                self.search_params,
                page_cursor=_next_cursor,
                included_relations=frozenset([(TROVE.searchResultPage,)]),
            )
            return self.handler(_next_params)
        return None


@dataclasses.dataclass
class ValuesearchHandle(BasicSearchHandle):
    search_result_page: typing.Iterable[ValuesearchResult] = ()


@dataclasses.dataclass
class TextMatchEvidence:
    property_path: tuple[str, ...]
    matching_highlight: primitive_rdf.Literal
    card_iri: typing.Optional[str]  # may be left implicit


@dataclasses.dataclass
class CardsearchResult:
    text_match_evidence: list[TextMatchEvidence]
    card_iri: str
    card_pk: str = ''

    @property
    def card_uuid(self) -> typing.Any:
        # card iri has the uuid at the end
        return primitive_rdf.iri_minus_namespace(
            self.card_iri,
            namespace=trove_indexcard_namespace(),
        )

    @property
    def card_id(self) -> str:
        return self.card_pk or self.card_uuid


@dataclasses.dataclass
class PropertypathUsage:
    property_path: tuple[str, ...]
    usage_count: int


@dataclasses.dataclass
class ValuesearchResult:
    value_iri: str | None
    value_value: str | None = None
    value_type: typing.Iterable[str] = ()
    name_text: typing.Iterable[str] = ()
    title_text: typing.Iterable[str] = ()
    label_text: typing.Iterable[str] = ()
    match_count: int = 0
    total_count: int = 0

    def __post_init__(self) -> None:
        assert (self.value_iri is not None) or (self.value_value is not None), (
            f'either value_iri or value_value required (on {self})'
        )


###
# types

TrovesearchHandler = typing.Callable[[BasicTroveParams], BasicSearchHandle]


###
# local helpers

def _cursor_value(cursor: PageCursor | None) -> str:
    return (
        cursor.as_queryparam_value()
        if cursor is not None and cursor.is_valid()
        else ''
    )
