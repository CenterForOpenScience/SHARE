import dataclasses
import typing


BoundedCount = typing.Union[
    int,
    typing.Literal[TROVE['ten-thousands-and-more']],
]


@dataclasses.dataclass
class IriMatchEvidence:
    property_path: typing.Iterable[str]  # ordered IRI path
    matching_iri: str
    card_id: typing.Optional[str]  # in case it's not the search-result card


@dataclasses.dataclass
class TextMatchEvidence:
    property_path: typing.Iterable[str]  # ordered IRI path
    matching_highlight: str
    card_id: typing.Optional[str]  # in case it's not the search-result card


@dataclasses.dataclass
class SearchResult:
    card_id: str
    card_result_count: typing.Optional[BoundedCount]
    match_evidence: typing.Iterable[typing.Union[IriMatchEvidence, TextMatchEvidence]]


@dataclasses.dataclass
class CardsearchResponse:
    result_count: BoundedCount
    search_result_set: typing.Iterable[SearchResult]
