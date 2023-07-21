import dataclasses
from typing import Literal, Iterable, Union, Optional

from gather import primitive_rdf

from share.search.search_request import PropertysearchParams
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
class SearchResult:
    text_match_evidence: Iterable[TextMatchEvidence]
    card_iri: str


@dataclasses.dataclass
class CardsearchResponse:
    total_result_count: BoundedCount
    search_result_page: Iterable[SearchResult]
    related_propertysearch_set: Iterable[PropertysearchParams]


@dataclasses.dataclass
class PropertysearchResponse:
    total_result_count: BoundedCount
    search_result_page: Iterable[SearchResult]


@dataclasses.dataclass
class ValuesearchResponse:
    total_result_count: BoundedCount
    search_result_page: Iterable[SearchResult]
