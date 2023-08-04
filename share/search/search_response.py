import dataclasses
from typing import Literal, Iterable, Union, Optional

from gather import primitive_rdf

from trove.vocab.namespaces import TROVE


BoundedCount = Union[
    int,  # exact count, if less than ten thousands
    Literal[TROVE['ten-thousands-and-more']],
]


# TODO: add `metadata={OWL.sameAs: ...}` to each field; use dataclass-to-rdf instead of gatherers

@dataclasses.dataclass
class TextMatchEvidence:
    property_path: tuple[str, ...]
    matching_highlight: primitive_rdf.Text
    card_iri: Optional[str]  # may be left implicit


@dataclasses.dataclass
class CardsearchResult:
    text_match_evidence: Iterable[TextMatchEvidence]
    card_iri: str


@dataclasses.dataclass
class CardsearchResponse:
    total_result_count: BoundedCount
    search_result_page: Iterable[CardsearchResult]
    next_page_cursor: Optional[str]
    prev_page_cursor: Optional[str]
    first_page_cursor: Optional[str]
    filtervalue_info: Iterable['ValuesearchResult']
    # related_propertysearch_set: Iterable[PropertysearchParams]


@dataclasses.dataclass
class PropertysearchResponse:
    total_result_count: BoundedCount
    search_result_page: Iterable[CardsearchResult]


@dataclasses.dataclass
class ValuesearchResult:
    value_iri: str
    value_type: Iterable[str] = ()
    name_text: Iterable[str] = ()
    title_text: Iterable[str] = ()
    label_text: Iterable[str] = ()
    match_count: int = 0
    total_count: int = 0


@dataclasses.dataclass
class ValuesearchResponse:
    total_result_count: int
    search_result_page: Iterable[ValuesearchResult]
    next_page_cursor: Optional[str]
    prev_page_cursor: Optional[str]
    first_page_cursor: Optional[str]
