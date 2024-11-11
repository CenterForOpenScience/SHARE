import dataclasses
from typing import Literal, Iterable, Union, Optional

from primitive_metadata import primitive_rdf

from trove.trovesearch.page_cursor import (
    PageCursor,
    ReproduciblyRandomSampleCursor,
)
from trove.trovesearch.search_params import (
    VALUESEARCH_MAX,
    CARDSEARCH_MAX,
    CardsearchParams,
)
from trove.vocab.namespaces import TROVE
from trove.vocab.trove import trove_indexcard_namespace


BoundedCount = Union[
    int,  # exact count, if less than ten thousands
    Literal[TROVE['ten-thousands-and-more']],
]


# TODO: add `metadata={OWL.sameAs: ...}` to each field; use dataclass-to-rdf instead of gatherers

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
        assert self.value_iri or self.value_value, (
            f'either value_iri or value_value required (on {self})'
        )


###
# paged responses

@dataclasses.dataclass
class PagedResponse:
    cursor: PageCursor

    @property
    def max_offset(self) -> int:
        raise NotImplementedError

    @property
    def total_result_count(self) -> BoundedCount:
        return (
            TROVE['ten-thousands-and-more']
            if (self.cursor is None) or self.cursor.has_many_more()
            else self.cursor.total_count
        )


@dataclasses.dataclass
class CardsearchResponse(PagedResponse):
    search_result_page: list[CardsearchResult]
    related_propertypath_results: list['PropertypathUsage']
    cardsearch_params: CardsearchParams

    max_offset = CARDSEARCH_MAX

    def __post_init__(self):
        _cursor = self.cursor
        if (
            isinstance(_cursor, ReproduciblyRandomSampleCursor)
            and _cursor.is_first_page()
        ):
            if _cursor.first_page_ids:
                # revisiting first page; reproduce original random order
                _ordering_by_id = {
                    _id: _i
                    for (_i, _id) in enumerate(_cursor.first_page_ids)
                }
                self.search_result_page.sort(key=lambda _r: _ordering_by_id[_r.card_id])
            else:
                _should_start_reproducible_randomness = (
                    not _cursor.has_many_more()
                    and any(
                        not _filter.is_type_filter()  # look for a non-default filter
                        for _filter in self.cardsearch_params.cardsearch_filter_set
                    )
                )
                if _should_start_reproducible_randomness:
                    _cursor.first_page_ids = [_result.card_id for _result in self.search_result_page]


@dataclasses.dataclass
class ValuesearchResponse(PagedResponse):
    search_result_page: Iterable[ValuesearchResult]

    max_offset = VALUESEARCH_MAX


###
# local helpers

def _cursor_value(cursor: PageCursor | None) -> str:
    return (
        cursor.as_queryparam_value()
        if cursor is not None and cursor.is_valid()
        else ''
    )
