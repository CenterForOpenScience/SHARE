from __future__ import annotations
import dataclasses
import logging
import urllib.parse
from typing import ClassVar, Any, TYPE_CHECKING

from primitive_metadata import gather
from primitive_metadata import primitive_rdf as rdf

from trove import models as trove_db
from trove.derive.osfmap_json import _RdfOsfmapJsonldRenderer
from trove.util.iris import get_sufficiently_unique_iri
from trove.vocab.namespaces import RDF, FOAF, DCTERMS, RDFS, DCAT, TROVE
from trove.vocab.jsonapi import (
    JSONAPI_LINK_OBJECT,
    JSONAPI_MEMBERNAME,
)
from trove.vocab import osfmap
from trove.vocab.trove import (
    TROVE_API_THESAURUS,
    trove_indexcard_namespace,
)
if TYPE_CHECKING:
    from collections.abc import Iterator, Iterable, Generator
    from trove.trovesearch.page_cursor import PageCursor
    from trove.trovesearch.search_handle import (
        CardsearchHandle,
        CardsearchResult,
        ValuesearchHandle,
        ValuesearchResult,
    )
    from trove.trovesearch.search_params import (
        CardsearchParams,
        SearchFilter,
        ValuesearchParams,
    )
    from trove.util.propertypath import (
        Propertypath,
        PropertypathSet,
    )


logger = logging.getLogger(__name__)


type GathererGenerator = Generator[rdf.RdfTriple | rdf.RdfTwople]


TROVE_GATHERING_NORMS = gather.GatheringNorms.new(
    namestory=(
        rdf.literal('cardsearch', language='en'),
        rdf.literal('search for "index cards" that describe resources', language='en'),
    ),
    focustype_iris={
        TROVE.Indexcard,
        TROVE.Cardsearch,
        TROVE.Valuesearch,
    },
    param_iris={TROVE.deriverIRI, TROVE.blendCards},
    thesaurus=TROVE_API_THESAURUS,
)


trovesearch_by_indexstrategy = gather.GatheringOrganizer(
    namestory=(
        rdf.literal('trove search', language='en'),
    ),
    norms=TROVE_GATHERING_NORMS,
    gatherer_params={
        'deriver_iri': TROVE.deriverIRI,
        'blend_cards': TROVE.blendCards,
    },
)


class _TypedFocus(gather.Focus):
    TYPE_IRI: ClassVar[str]  # (expected on subclasses)
    ADDITIONAL_TYPE_IRIS: ClassVar[tuple[str, ...]] = ()  # (optional on subclasses)

    @classmethod
    def new(cls, *args: Any, type_iris: Iterable[str] = (), **kwargs: Any) -> Any:
        return super().new(
            *args,
            # add type_iri to new Focus instance
            type_iris={
                cls.TYPE_IRI,
                *getattr(cls, 'ADDITIONAL_TYPE_IRIS', ()),
                *type_iris
            },
            **kwargs,
        )


@dataclasses.dataclass(frozen=True)
class CardsearchFocus(_TypedFocus):
    TYPE_IRI = TROVE.Cardsearch

    # additional dataclass fields
    search_params: CardsearchParams = dataclasses.field(compare=False)
    search_handle: CardsearchHandle = dataclasses.field(compare=False)


@dataclasses.dataclass(frozen=True)
class ValuesearchFocus(_TypedFocus):
    TYPE_IRI = TROVE.Valuesearch

    # additional dataclass fields
    search_params: ValuesearchParams = dataclasses.field(compare=False)
    search_handle: ValuesearchHandle = dataclasses.field(compare=False)


@dataclasses.dataclass(frozen=True)
class IndexcardFocus(_TypedFocus):
    TYPE_IRI: ClassVar[str] = TROVE.Indexcard
    ADDITIONAL_TYPE_IRIS: ClassVar[tuple[str, ...]] = (DCAT.CatalogRecord,)

    # additional dataclass fields
    indexcard: trove_db.Indexcard = dataclasses.field(compare=False)
    resourceMetadata: Any = dataclasses.field(compare=False, default=None, repr=False)


# TODO: per-field text search in rdf
# @trovesearch_by_indexstrategy.gatherer(TROVE.cardSearchText)
# def gather_cardsearch_text(focus: CardsearchFocus, **kwargs):
#     yield (TROVE.cardSearchText, literal(search_params.cardsearch_text))
#
#
# @trovesearch_by_indexstrategy.gatherer(TROVE.valueSearchText)
# def gather_valuesearch_text(focus, **kwargs):
#     yield (TROVE.valueSearchText, literal(search_params.valuesearch_text))


@trovesearch_by_indexstrategy.gatherer(TROVE.propertyPath, focustype_iris={TROVE.Valuesearch})
def gather_valuesearch_propertypath(focus: ValuesearchFocus, **kwargs: Any) -> GathererGenerator:
    yield from _single_propertypath_twoples(focus.search_params.valuesearch_propertypath)


@trovesearch_by_indexstrategy.gatherer(TROVE.valueSearchFilter)
def gather_valuesearch_filter(focus: ValuesearchFocus, **kwargs: Any) -> GathererGenerator:
    for _filter in focus.search_params.valuesearch_filter_set:
        yield TROVE.valueSearchFilter, _filter_as_blanknode(_filter)


@trovesearch_by_indexstrategy.gatherer(TROVE.totalResultCount)
def gather_count(focus: CardsearchFocus, **kwargs: Any) -> GathererGenerator:
    yield TROVE.totalResultCount, focus.search_handle.total_result_count


@trovesearch_by_indexstrategy.gatherer(
    TROVE.searchResultPage,
    focustype_iris={TROVE.Cardsearch},
    cache_bound=1,  # only the first page gets cached
)
def gather_cardsearch_page(focus: CardsearchFocus, *, deriver_iri: str, blend_cards: bool, **kwargs: Any) -> GathererGenerator:
    # each searchResultPage a sequence of search results
    _current_handle: CardsearchHandle | None = focus.search_handle
    while _current_handle is not None:
        _result_page = []
        _card_foci = _load_cards_and_contents(
            card_iris=(_result.card_iri for _result in _current_handle.search_result_page),
            deriver_iri=deriver_iri,
        )
        for _result in _current_handle.search_result_page or ():
            _card_focus = _card_foci.get(_result.card_iri)
            if _card_focus is None:
                continue  # skip (deleted card still indexed?)
            _result_obj, _triples = (
                _blended_card(_card_focus)
                if blend_cards
                else _unblended_card(_result, _card_focus)
            )
            _result_page.append(_result_obj)
            yield from _triples
        yield (TROVE.searchResultPage, rdf.sequence(_result_page))
        _current_handle = _current_handle.get_next_streaming_handle()


def _blended_card(card_focus: IndexcardFocus) -> tuple[rdf.RdfObject, Iterable[rdf.RdfTriple]]:
    _metadata = card_focus.resourceMetadata
    if isinstance(_metadata, rdf.Literal):
        return (_metadata, ())
    if isinstance(_metadata, rdf.QuotedGraph):
        return (_metadata.focus_iri, rdf.iter_tripleset(_metadata.tripledict))
    return (card_focus.single_iri(), ())  # oh well


def _unblended_card(_result: CardsearchResult, _card_focus: IndexcardFocus) -> tuple[rdf.RdfObject, Iterable[rdf.RdfTriple]]:
    return (
        _unblended_cardsearch_result(_result),
        _unblended_card_triples(_result, _card_focus),
    )


def _unblended_cardsearch_result(_result: CardsearchResult) -> rdf.RdfBlanknode:
    _text_evidence_twoples = (
        (TROVE.matchEvidence, frozenset((
            (RDF.type, TROVE.TextMatchEvidence),
            (TROVE.matchingHighlight, _evidence.matching_highlight),
            (TROVE.evidenceCardIdentifier, rdf.literal(_evidence.card_iri)),
            *_single_propertypath_twoples(_evidence.property_path),
        )))
        for _evidence in _result.text_match_evidence
    )
    return frozenset((
        (RDF.type, TROVE.SearchResult),
        (TROVE.indexCard, _result.card_iri),
        *_text_evidence_twoples,
    ))


def _unblended_card_triples(_result: CardsearchResult, _card_focus: IndexcardFocus) -> Iterator[rdf.RdfTriple]:
    # hack around (current) limitations of primitive_metadata.gather
    # (what with all these intermediate blank nodes and sequences):
    # yield trove:resourceMetadata here (instead of another gatherer)
    _card_twoples = _unblended_indexcard_twoples(
        focus_identifiers=[
            _identifier.as_iri()
            for _identifier in _card_focus.indexcard.focus_identifier_set.all()
        ],
        resource_metadata=_card_focus.resourceMetadata,
    )
    for _pred, _obj in _card_twoples:
        yield (_result.card_iri, _pred, _obj)


@trovesearch_by_indexstrategy.gatherer(TROVE.searchResultPage)
def gather_page_links(focus: CardsearchFocus, **kwargs: Any) -> GathererGenerator:
    # links to more pages of results
    yield from _search_page_links(focus, focus.search_params)


@trovesearch_by_indexstrategy.gatherer(
    TROVE.relatedPropertyList,
    focustype_iris={TROVE.Cardsearch},
)
def gather_related_properties(focus: CardsearchFocus, **kwargs: Any) -> GathererGenerator:
    # info about related properties (for refining/filtering further)
    _prop_usage_counts: dict[tuple[str, ...], int] = {
        _prop_result.property_path: _prop_result.usage_count
        for _prop_result in focus.search_handle.related_propertypath_results
    }
    _relatedproperty_list: list[frozenset[tuple[str, Any]]] = [
        _related_property_result(_propertypath, _prop_usage_counts.get(_propertypath, 0))
        for _propertypath in focus.search_params.related_property_paths
    ]
    if _relatedproperty_list:
        yield TROVE.relatedPropertyList, rdf.sequence(_relatedproperty_list)


@trovesearch_by_indexstrategy.gatherer(TROVE.cardSearchFilter)
def gather_cardsearch_filter(focus: CardsearchFocus, **kwargs: Any) -> GathererGenerator:
    # filter-values from search params
    for _filter in focus.search_params.cardsearch_filter_set:
        yield TROVE.cardSearchFilter, _filter_as_blanknode(_filter)


@trovesearch_by_indexstrategy.gatherer(
    TROVE.searchResultPage,
    focustype_iris={TROVE.Valuesearch},
)
def gather_valuesearch_page(focus: ValuesearchFocus, *, deriver_iri: str, blend_cards: bool, **kwargs: Any) -> GathererGenerator:
    _result_page: list[rdf.Blanknode] = []
    _value_iris: set[str] = {
        _result.value_iri
        for _result in focus.search_handle.search_result_page or ()
        if _result.value_iri
    }
    if _value_iris:
        _card_foci = _load_cards_and_contents(value_iris=_value_iris, deriver_iri=deriver_iri)
    else:
        _card_foci = {}
    _card_foci_by_suffuniq_iri: dict[str, IndexcardFocus] = {
        _identifier.sufficiently_unique_iri: _focus
        for _focus in _card_foci.values()
        for _identifier in _focus.indexcard.focus_identifier_set.all()
    }
    for _result in focus.search_handle.search_result_page or ():
        _indexcard_obj: rdf.Blanknode | None = None
        if _result.value_iri is not None:
            _card_focus = _card_foci_by_suffuniq_iri.get(
                get_sufficiently_unique_iri(_result.value_iri),
            )
            if _card_focus is not None:
                _indexcard_obj = _card_focus.indexcard.get_iri()
                # hack around (current) limitations of primitive_metadata.gather
                # (what with all these intermediate blank nodes and sequences):
                # yield trove:resourceMetadata here (instead of another gatherer)
                _card_twoples = _unblended_indexcard_twoples(
                    focus_identifiers=[
                        _identifier.as_iri()
                        for _identifier in _card_focus.indexcard.focus_identifier_set.all()
                    ],
                    resource_metadata=_card_focus.resourceMetadata,
                )
                for _pred, _obj in _card_twoples:
                    yield _indexcard_obj, _pred, _obj
        if _indexcard_obj is None:
            # no actual indexcard; put what we know in a blanknode-indexcard
            _indexcard_obj = _valuesearch_result_as_indexcard_blanknode(_result)
        _result_page.append(rdf.blanknode({
            RDF.type: {TROVE.SearchResult},
            TROVE.cardsearchResultCount: {_result.match_count},
            TROVE.indexCard: {_indexcard_obj},
        }))
    yield TROVE.searchResultPage, rdf.sequence(_result_page)


@trovesearch_by_indexstrategy.gatherer(
    TROVE.totalResultCount,
    focustype_iris={TROVE.Valuesearch},
)
def gather_valuesearch_count(focus: ValuesearchFocus, **kwargs: Any) -> GathererGenerator:
    yield (TROVE.totalResultCount, focus.search_handle.total_result_count)


# @trovesearch_by_indexstrategy.gatherer(
#     focustype_iris={TROVE.Indexcard},
# )
# def gather_card(focus, *, deriver_iri, **kwargs):
#     yield from _card_triples(...)
#     _indexcard_namespace = trove_indexcard_namespace()
#     try:
#         _indexcard_iri = next(
#             _iri
#             for _iri in focus.iris
#             if _iri in _indexcard_namespace
#         )
#     except StopIteration:
#         raise trove_exceptions.IriMismatch(f'could not find indexcard iri in {focus.iris} (looking for {_indexcard_namespace})')


@trovesearch_by_indexstrategy.gatherer(DCTERMS.issued, focustype_iris={TROVE.Indexcard})
def gather_card_issued(focus: IndexcardFocus, **kwargs: Any) -> GathererGenerator:
    yield DCTERMS.issued, focus.indexcard.created.date()


@trovesearch_by_indexstrategy.gatherer(DCTERMS.modified, focustype_iris={TROVE.Indexcard})
def gather_card_modified(focus: IndexcardFocus, **kwargs: Any) -> GathererGenerator:
    yield DCTERMS.modified, focus.indexcard.modified.date()


@trovesearch_by_indexstrategy.gatherer(
    FOAF.primaryTopic,
    TROVE.focusIdentifier,
    focustype_iris={TROVE.Indexcard},
)
def gather_primary_topic(focus: IndexcardFocus, **kwargs: Any) -> GathererGenerator:
    for _identifier in focus.indexcard.focus_identifier_set.all():
        _iri = _identifier.as_iri()
        yield (FOAF.primaryTopic, _iri)
        yield (TROVE.focusIdentifier, rdf.literal(_iri))


@trovesearch_by_indexstrategy.gatherer(
    TROVE.resourceMetadata,
    focustype_iris={TROVE.Indexcard},
)
def gather_card_contents(focus: IndexcardFocus, *, deriver_iri: str, **kwargs: Any) -> GathererGenerator:
    if focus.resourceMetadata is not None:
        yield (TROVE.resourceMetadata, focus.resourceMetadata)
    else:
        _iri = focus.single_iri()
        _loaded_foci = _load_cards_and_contents(card_iris=[_iri], deriver_iri=deriver_iri)
        _loaded_metadata = _loaded_foci[_iri].resourceMetadata
        yield (TROVE.resourceMetadata, _loaded_metadata)


def _load_cards_and_contents(
    *,
    card_iris: Iterable[str] | None = None,
    value_iris: Iterable[str] | None = None,
    deriver_iri: str,
) -> dict[str, IndexcardFocus]:
    return (
        _load_cards_and_extracted_rdf_contents(card_iris, value_iris)
        if deriver_iri is None
        else _load_cards_and_derived_contents(card_iris, value_iris, deriver_iri)
    )


def _load_cards_and_extracted_rdf_contents(
    card_iris: Iterable[str] | None = None,
    value_iris: Iterable[str] | None = None,
) -> dict[str, IndexcardFocus]:
    _card_namespace = trove_indexcard_namespace()
    _resource_description_qs = (
        trove_db.LatestResourceDescription.objects
        .select_related('indexcard')
        .prefetch_related('indexcard__focus_identifier_set')
    )
    if card_iris is not None:
        _indexcard_uuids = {
            rdf.iri_minus_namespace(_card_iri, namespace=_card_namespace)
            for _card_iri in card_iris
        }
        _resource_description_qs = _resource_description_qs.filter(indexcard__uuid__in=_indexcard_uuids)
    if value_iris is not None:
        _resource_description_qs = _resource_description_qs.filter(
            indexcard__focus_identifier_set__in=(
                trove_db.ResourceIdentifier.objects
                .queryset_for_iris(value_iris)
            ),
        )
    _card_foci: dict[str, IndexcardFocus] = {}
    for _resource_description in _resource_description_qs:
        _card = _resource_description.indexcard
        _card_iri = _card.get_iri()
        _quoted_graph = _resource_description.as_quoted_graph()
        _quoted_graph.add(
            (_quoted_graph.focus_iri, FOAF.isPrimaryTopicOf, _card_iri),
        )
        _card_foci[_card_iri] = IndexcardFocus.new(
            iris=_card_iri,
            indexcard=_card,
            resourceMetadata=_quoted_graph,
        )
    return _card_foci


def _load_cards_and_derived_contents(
    card_iris: Iterable[str] | None,
    value_iris: Iterable[str] | None,
    deriver_iri: str,
) -> dict[str, IndexcardFocus]:
    _card_namespace = trove_indexcard_namespace()
    # include pre-formatted data from a DerivedIndexcard
    _derived_indexcard_qs = (
        trove_db.DerivedIndexcard.objects
        .filter(
            deriver_identifier__in=(
                trove_db.ResourceIdentifier.objects
                .queryset_for_iri(deriver_iri)
            ),
        )
        .select_related('upriver_indexcard', 'deriver_identifier')
        .prefetch_related('upriver_indexcard__focus_identifier_set')
    )
    if card_iris is not None:
        _indexcard_uuids = {
            rdf.iri_minus_namespace(_card_iri, namespace=_card_namespace)
            for _card_iri in card_iris
        }
        _derived_indexcard_qs = _derived_indexcard_qs.filter(
            upriver_indexcard__uuid__in=_indexcard_uuids,
        )
    if value_iris is not None:
        _derived_indexcard_qs = _derived_indexcard_qs.filter(
            upriver_indexcard__focus_identifier_set__in=(
                trove_db.ResourceIdentifier.objects
                .queryset_for_iris(value_iris)
            ),
        )
    _card_foci: dict[str, IndexcardFocus] = {}
    for _derived in _derived_indexcard_qs:
        _card_iri = _derived.upriver_indexcard.get_iri()
        _card_foci[_card_iri] = IndexcardFocus.new(
            iris=_card_iri,
            indexcard=_derived.upriver_indexcard,
            resourceMetadata=_derived.as_rdf_literal(),
        )
    return _card_foci


###
# local helpers

def _filter_as_blanknode(search_filter: SearchFilter) -> frozenset[rdf.RdfTwople]:
    _filter_twoples = [
        (TROVE.filterType, search_filter.operator.value),
        *_multi_propertypath_twoples(search_filter.propertypath_set),
    ]
    if not search_filter.operator.is_valueless_operator():
        for _value in search_filter.value_set:
            if search_filter.operator.is_iri_operator():
                _valueinfo = _osfmap_or_unknown_iri_as_json(_value)
            else:
                _valueinfo = rdf.literal_json({'@value': _value})
            _filter_twoples.append((TROVE.filterValue, _valueinfo))
    return frozenset(_filter_twoples)


def _osfmap_or_unknown_iri_as_json(iri: str) -> rdf.Literal:
    try:
        _twopledict = osfmap.OSFMAP_THESAURUS[iri]
    except KeyError:
        return rdf.literal_json({'@id': iri})
    else:
        return _osfmap_json({iri: _twopledict}, focus_iri=iri)


def _valuesearch_result_as_json(result: ValuesearchResult) -> rdf.Literal:
    _value_twopledict = {
        RDF.type: set(result.value_type),
        FOAF.name: set(map(rdf.literal, result.name_text)),
        DCTERMS.title: set(map(rdf.literal, result.title_text)),
        RDFS.label: set(map(rdf.literal, result.label_text)),
    }
    return (
        _osfmap_json({result.value_iri: _value_twopledict}, result.value_iri)
        if result.value_iri
        else _osfmap_twople_json(_value_twopledict)
    )


def _unblended_indexcard_twoples(
    focus_identifiers: Iterable[str],
    resource_metadata: rdf.Literal,
) -> Iterator[rdf.RdfTwople]:
    yield RDF.type, TROVE.Indexcard
    for _identifier in focus_identifiers:
        yield (TROVE.focusIdentifier, (
            _identifier
            if isinstance(_identifier, rdf.Literal)
            else rdf.literal(_identifier)
        ))
    yield TROVE.resourceMetadata, resource_metadata


def _valuesearch_result_as_indexcard_blanknode(result: ValuesearchResult) -> rdf.Blanknode:
    return frozenset(_unblended_indexcard_twoples(
        focus_identifiers=[rdf.literal(result.value_iri or result.value_value)],
        resource_metadata=_valuesearch_result_as_json(result),
    ))


def _osfmap_json(tripledict: rdf.RdfTripleDictionary, focus_iri: str) -> rdf.Literal:
    return rdf.literal_json(
        _RdfOsfmapJsonldRenderer().tripledict_as_nested_jsonld(tripledict, focus_iri)
    )


def _osfmap_twople_json(twopledict: rdf.RdfTwopleDictionary) -> rdf.Literal:
    return rdf.literal_json(
        _RdfOsfmapJsonldRenderer().twopledict_as_jsonld(twopledict)
    )


def _osfmap_path(property_path: Propertypath) -> rdf.Literal:
    return rdf.literal_json([
        osfmap.osfmap_json_shorthand().compact_iri(_iri)
        for _iri in property_path
    ])


def _single_propertypath_twoples(property_path: Propertypath) -> Generator[rdf.RdfTwople]:
    yield (TROVE.propertyPathKey, rdf.literal(osfmap.osfmap_propertypath_key(property_path)))
    yield (TROVE.propertyPath, _propertypath_sequence(property_path))
    yield (TROVE.osfmapPropertyPath, _osfmap_path(property_path))


def _multi_propertypath_twoples(propertypath_set: PropertypathSet) -> Generator[rdf.RdfTwople]:
    yield (TROVE.propertyPathKey, rdf.literal(osfmap.osfmap_propertypath_set_key(propertypath_set)))
    for _path in propertypath_set:
        yield TROVE.propertyPathSet, _propertypath_sequence(_path)


def _propertypath_sequence(property_path: Propertypath) -> Any:
    _propertypath_metadata = []
    for _property_iri in property_path:
        try:
            _property_twopledict = osfmap.OSFMAP_THESAURUS[_property_iri]
        except KeyError:
            _property_twopledict = {RDF.type: {RDF.Property}}  # giving benefit of the doubt
        _propertypath_metadata.append(_osfmap_json(
            {_property_iri: _property_twopledict},
            focus_iri=_property_iri,
        ))
    return rdf.sequence(_propertypath_metadata)


def _related_property_result(property_path: Propertypath, count: int) -> rdf.Blanknode:
    return frozenset((
        (RDF.type, TROVE.RelatedPropertypath),
        (TROVE.cardsearchResultCount, count),
        (TROVE.suggestedFilterOperator, rdf.literal(osfmap.osfmap_json_shorthand().compact_iri(
            osfmap.suggested_filter_operator(property_path[-1]),
        ))),
        *_single_propertypath_twoples(property_path),
    ))


def _search_page_links(search_focus: Any, search_params: Any) -> Iterator[rdf.RdfTwople]:
    _search_iri_split = urllib.parse.urlsplit(next(iter(search_focus.iris)))

    def _iri_with_cursor(page_cursor: PageCursor) -> Any:
        return urllib.parse.urlunsplit((
            _search_iri_split.scheme,
            _search_iri_split.netloc,
            _search_iri_split.path,
            dataclasses.replace(search_params, page_cursor=page_cursor).to_querystring(),
            _search_iri_split.fragment,
        ))

    _next = search_focus.search_handle.cursor.next_cursor()
    if _next is not None and _next.is_valid():
        yield (TROVE.searchResultPage, _jsonapi_link('next', _iri_with_cursor(_next)))
    _prev = search_focus.search_handle.cursor.prev_cursor()
    if _prev is not None and _prev.is_valid():
        yield (TROVE.searchResultPage, _jsonapi_link('prev', _iri_with_cursor(_prev)))
    _first = search_focus.search_handle.cursor.first_cursor()
    if _first is not None and _first.is_valid():
        yield (TROVE.searchResultPage, _jsonapi_link('first', _iri_with_cursor(_first)))


def _jsonapi_link(membername: str, iri: str) -> frozenset[tuple[str, Any]]:
    return frozenset((
        (RDF.type, JSONAPI_LINK_OBJECT),
        (JSONAPI_MEMBERNAME, rdf.literal(membername)),
        (RDF.value, iri),
    ))
