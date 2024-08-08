import dataclasses
from typing import Literal, Iterable, Union, Optional

from primitive_metadata import primitive_rdf

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
    text_match_evidence: Iterable[TextMatchEvidence]
    card_iri: str
    card_uuid: str = ''
    card_pk: str = ''  # TODO: use or remove

    def __post_init__(self):
        if not self.card_uuid:
            # card iri has the uuid at the end
            self.card_uuid = primitive_rdf.iri_minus_namespace(
                self.card_iri,
                namespace=trove_indexcard_namespace(),
            )


@dataclasses.dataclass
class CardsearchResponse:
    total_result_count: BoundedCount
    search_result_page: Iterable[CardsearchResult]
    next_page_cursor: Optional[str]
    prev_page_cursor: Optional[str]
    first_page_cursor: Optional[str]
    related_propertypath_results: Iterable['PropertypathUsage']


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


@dataclasses.dataclass
class ValuesearchResponse:
    search_result_page: Iterable[ValuesearchResult]
    total_result_count: Optional[int] = None
    next_page_cursor: Optional[str] = None
    prev_page_cursor: Optional[str] = None
    first_page_cursor: Optional[str] = None
