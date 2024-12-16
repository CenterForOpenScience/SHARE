from __future__ import annotations
import dataclasses
import functools
import itertools
from typing import Literal, Iterable, Union, Optional, Generator

from primitive_metadata import primitive_rdf

from trove.trovesearch.page_cursor import (
    PageCursor,
    ReproduciblyRandomSampleCursor,
)
from trove.trovesearch.search_params import (
    CardsearchParams,
    ValuesearchParams,
)
from trove.vocab.namespaces import TROVE
from trove.vocab.trove import trove_indexcard_namespace

# TODO: add `metadata={OWL.sameAs: ...}` to each field; use dataclass-to-rdf to simplify gatherers


BoundedCount = Union[
    int,  # exact count, if less than ten thousands
    Literal[TROVE['ten-thousands-and-more']],
]


@dataclasses.dataclass
class BasicSearchHandle:
    cursor: PageCursor
    search_result_generator: Generator

    @property
    def total_result_count(self) -> BoundedCount:
        return (
            TROVE['ten-thousands-and-more']
            if self.cursor.has_many_more()
            else self.cursor.total_count
        )

    @functools.cached_property
    def search_result_page(self) -> tuple:
        # note: use either search_result_page or search_result_generator, not both
        return tuple(
            itertools.islice(self.search_result_generator, self.cursor.page_size)
        )


@dataclasses.dataclass
class CardsearchHandle(BasicSearchHandle):
    related_propertypath_results: list[PropertypathUsage]
    cardsearch_params: CardsearchParams

    def __post_init__(self):
        _cursor = self.cursor
        if (  # TODO: move this logic into the... index strategy?
            isinstance(_cursor, ReproduciblyRandomSampleCursor)
            and _cursor.is_first_page()
            and not _cursor.first_page_ids
            and not _cursor.has_many_more()
        ):
            _cursor.first_page_ids = [_result.card_id for _result in self.search_result_page]

    @functools.cached_property
    def search_result_page(self) -> tuple:
        _page = super().search_result_page
        if (
            isinstance(self.cursor, ReproduciblyRandomSampleCursor)
            and self.cursor.is_first_page()
            and self.cursor.first_page_ids
        ):
            # revisiting first page; reproduce original random order
            _ordering_by_id = {
                _id: _i
                for (_i, _id) in enumerate(self.cursor.first_page_ids)
            }
            return tuple(
                sorted(
                    _page,
                    key=lambda _r: _ordering_by_id[_r.card_id],
                ),
            )
        return _page


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
        assert self.value_iri or self.value_value, (
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
