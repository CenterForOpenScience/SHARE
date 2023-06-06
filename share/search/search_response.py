import dataclasses
import typing

import gather

from share.search.search_request import PropertysearchParams
from share.search.trovesearch_gathering import TROVE


BoundedCount = typing.Union[
    int,  # exact count, if less than ten thousands
    typing.Literal[TROVE['ten-thousands-and-more']],
]


@dataclasses.dataclass
class TextMatchEvidence:
    property_path: tuple[str, ...]
    matching_highlight: gather.text
    card_iri: typing.Optional[str]  # may be left implicit


@dataclasses.dataclass
class SearchResult:
    text_match_evidence: typing.Iterable[TextMatchEvidence]
    card_iri: str


@dataclasses.dataclass
class CardsearchResponse:
    total_result_count: BoundedCount
    search_result_page: typing.Iterable[SearchResult]
    related_propertysearch_set: typing.Iterable[PropertysearchParams]


@dataclasses.dataclass
class PropertysearchResponse:
    total_result_count: BoundedCount
    search_result_page: typing.Iterable[SearchResult]


@dataclasses.dataclass
class ValuesearchResponse:
    total_result_count: BoundedCount
    search_result_page: typing.Iterable[SearchResult]
