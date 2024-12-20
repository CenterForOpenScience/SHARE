import dataclasses
import logging
import urllib.parse
from typing import ClassVar

from primitive_metadata.primitive_rdf import (
    Literal,
    blanknode,
    iri_minus_namespace,
    literal,
    sequence,
)
from primitive_metadata import gather
from primitive_metadata import primitive_rdf as rdf

from trove import models as trove_db
from trove.derive.osfmap_json import _RdfOsfmapJsonldRenderer
from trove.trovesearch.page_cursor import PageCursor
from trove.trovesearch.search_params import (
    CardsearchParams,
    ValuesearchParams,
    propertypath_key,
    propertypath_set_key,
)
from trove.trovesearch.search_handle import (
    CardsearchHandle,
    ValuesearchHandle,
    ValuesearchResult,
)
from trove.vocab.namespaces import RDF, FOAF, DCTERMS, RDFS, DCAT, TROVE
from trove.vocab.jsonapi import (
    JSONAPI_LINK_OBJECT,
    JSONAPI_MEMBERNAME,
)
from trove.vocab.osfmap import (
    osfmap_shorthand,
    OSFMAP_THESAURUS,
    suggested_filter_operator,
)
from trove.vocab.trove import (
    TROVE_API_THESAURUS,
    trove_indexcard_namespace,
    trove_shorthand,
)


logger = logging.getLogger(__name__)


TROVE_GATHERING_NORMS = gather.GatheringNorms.new(
    namestory=(
        literal('cardsearch', language='en'),
        literal('search for "index cards" that describe resources', language='en'),
    ),
    focustype_iris={
        TROVE.Indexcard,
        TROVE.Cardsearch,
        TROVE.Valuesearch,
    },
    thesaurus=TROVE_API_THESAURUS,
)


trovesearch_by_indexstrategy = gather.GatheringOrganizer(
    namestory=(
        literal('trove search', language='en'),
    ),
    norms=TROVE_GATHERING_NORMS,
    gatherer_params={
        'deriver_iri': TROVE.deriverIRI,
    },
)


class _TypedFocus(gather.Focus):
    TYPE_IRI: ClassVar[str]  # (expected on subclasses)
    ADDITIONAL_TYPE_IRIS: ClassVar[tuple[str, ...]] = ()  # (optional on subclasses)

    @classmethod
    def new(cls, *, type_iris=(), **kwargs):
        return super().new(
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


class IndexcardFocus(_TypedFocus):
    TYPE_IRI = TROVE.Indexcard
    ADDITIONAL_TYPE_IRIS = (DCAT.CatalogRecord,)


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
def gather_valuesearch_propertypath(focus: ValuesearchFocus, **kwargs):
    yield from _single_propertypath_twoples(focus.search_params.valuesearch_propertypath)


@trovesearch_by_indexstrategy.gatherer(TROVE.valueSearchFilter)
def gather_valuesearch_filter(focus, **kwargs):
    for _filter in focus.search_params.valuesearch_filter_set:
        yield (TROVE.valueSearchFilter, _filter_as_blanknode(_filter))


@trovesearch_by_indexstrategy.gatherer(TROVE.totalResultCount)
def gather_count(focus: CardsearchFocus, **kwargs):
    yield (TROVE.totalResultCount, focus.search_handle.total_result_count)


@trovesearch_by_indexstrategy.gatherer(
    TROVE.searchResultPage,
    focustype_iris={TROVE.Cardsearch},
    cache_bound=1,  # only the first page gets cached
)
def gather_cardsearch_page(focus: CardsearchFocus, *, deriver_iri, **kwargs):
    # each searchResultPage a sequence of search results
    _current_handle: CardsearchHandle | None = focus.search_handle
    while _current_handle is not None:
        _result_page = []
        _card_descriptions_by_iri = _load_card_descriptions(_current_handle.search_result_page, deriver_iri)
        for _result in _current_handle.search_result_page or ():
            _text_evidence_twoples = (
                (TROVE.matchEvidence, frozenset((
                    (RDF.type, TROVE.TextMatchEvidence),
                    (TROVE.matchingHighlight, _evidence.matching_highlight),
                    (TROVE.evidenceCardIdentifier, literal(_evidence.card_iri)),
                    *_single_propertypath_twoples(_evidence.property_path),
                )))
                for _evidence in _result.text_match_evidence
            )
            _result_page.append(frozenset((
                (RDF.type, TROVE.SearchResult),
                (TROVE.indexCard, _result.card_iri),
                *_text_evidence_twoples,
            )))
            try:
                _card_description = _card_descriptions_by_iri[_result.card_iri]
            except KeyError:
                pass
            else:
                yield from rdf.iter_tripleset(_card_description.tripledict)
        yield (TROVE.searchResultPage, sequence(_result_page))
        _current_handle = _current_handle.get_next_streaming_handle()


@trovesearch_by_indexstrategy.gatherer(TROVE.searchResultPage)
def gather_page_links(focus, **kwargs):
    # links to more pages of results
    yield from _search_page_links(focus, focus.search_params)


@trovesearch_by_indexstrategy.gatherer(
    TROVE.relatedPropertyList,
    focustype_iris={TROVE.Cardsearch},
)
def gather_related_properties(focus, **kwargs):
    # info about related properties (for refining/filtering further)
    _prop_usage_counts = {
        _prop_result.property_path: _prop_result.usage_count
        for _prop_result in focus.search_handle.related_propertypath_results
    }
    _relatedproperty_list = [
        _related_property_result(_propertypath, _prop_usage_counts.get(_propertypath, 0))
        for _propertypath in focus.search_params.related_property_paths
    ]
    if _relatedproperty_list:
        yield (TROVE.relatedPropertyList, sequence(_relatedproperty_list))


@trovesearch_by_indexstrategy.gatherer(TROVE.cardSearchFilter)
def gather_cardsearch_filter(focus, **kwargs):
    # filter-values from search params
    for _filter in focus.search_params.cardsearch_filter_set:
        yield (TROVE.cardSearchFilter, _filter_as_blanknode(_filter))


@trovesearch_by_indexstrategy.gatherer(
    TROVE.searchResultPage,
    focustype_iris={TROVE.Valuesearch},
)
def gather_valuesearch_page(focus: ValuesearchFocus, **kwargs):
    _result_page = []
    _value_iris = {
        _result.value_iri
        for _result in focus.search_handle.search_result_page or ()
        if _result.value_iri
    }
    if _value_iris:
        _value_indexcards = (
            trove_db.Indexcard.objects
            .filter(
                focus_identifier_set__in=(
                    trove_db.ResourceIdentifier.objects
                    .queryset_for_iris(_value_iris)
                ),
                derived_indexcard_set__deriver_identifier__in=(
                    trove_db.ResourceIdentifier.objects
                    .queryset_for_iri(TROVE['derive/osfmap_json'])
                    # TODO: choose deriver by queryparam/gatherer-kwarg
                ),
            )
            .prefetch_related('focus_identifier_set')
        )
    else:
        _value_indexcards = []
    for _result in focus.search_handle.search_result_page or ():
        _indexcard_obj = None
        if _result.value_iri in _value_iris:
            for _indexcard in _value_indexcards:
                if any(
                    _identifier.equivalent_to_iri(_result.value_iri)
                    for _identifier in _indexcard.focus_identifier_set.all()
                ):
                    _indexcard_obj = _indexcard.get_iri()
                    yield (_indexcard_obj, RDF.type, TROVE.Indexcard)  # so gather_card runs
                    # TODO: batch-load cards instead
                    break  # found the indexcard
        if _indexcard_obj is None:
            # no actual indexcard; put what we know in a blanknode-indexcard
            _indexcard_obj = _valuesearch_result_as_indexcard_blanknode(_result)
        _result_page.append(blanknode({
            RDF.type: {TROVE.SearchResult},
            TROVE.cardsearchResultCount: {_result.match_count},
            TROVE.indexCard: {_indexcard_obj},
        }))
    yield (TROVE.searchResultPage, sequence(_result_page))


@trovesearch_by_indexstrategy.gatherer(
    TROVE.totalResultCount,
    focustype_iris={TROVE.Valuesearch},
)
def gather_valuesearch_count(focus, **kwargs):
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


def _load_card_descriptions(search_result_page, deriver_iri) -> dict[str, rdf.RdfGraph]:
    _card_iris = {_result.card_iri for _result in search_result_page}
    return (
        _load_card_descriptions_nonderived(_card_iris)
        if deriver_iri is None
        else _load_card_descriptions_derived(_card_iris, deriver_iri)
    )


def _load_card_descriptions_nonderived(card_iris) -> dict[str, rdf.RdfGraph]:
    _card_namespace = trove_indexcard_namespace()
    _indexcard_uuids = {
        iri_minus_namespace(_card_iri, namespace=_card_namespace)
        for _card_iri in card_iris
    }
    _indexcard_rdf_qs = (
        trove_db.LatestIndexcardRdf.objects
        .filter(indexcard__uuid__in=_indexcard_uuids)
        .select_related('indexcard')
        .prefetch_related('indexcard__focus_identifier_set')
    )
    _by_card_iri = {}
    for _indexcard_rdf in _indexcard_rdf_qs:
        _indexcard_iri = _indexcard_rdf.indexcard.get_iri()
        _quoted_graph = _indexcard_rdf.as_quoted_graph()
        _quoted_graph.add(
            (_quoted_graph.focus_iri, FOAF.primaryTopicOf, _indexcard_iri),
        )
        _by_card_iri[_indexcard_iri] = _describe_indexcard_nonderived(
            _indexcard_iri, _indexcard_rdf
        )
    return _by_card_iri


def _load_card_descriptions_derived(card_iris, deriver_iri: str) -> dict[str, rdf.RdfGraph]:
    _card_namespace = trove_indexcard_namespace()
    _indexcard_uuids = {
        iri_minus_namespace(_card_iri, namespace=_card_namespace)
        for _card_iri in card_iris
    }
    # include pre-formatted data from a DerivedIndexcard
    _derived_indexcard_qs = (
        trove_db.DerivedIndexcard.objects
        .filter(
            upriver_indexcard__uuid__in=_indexcard_uuids,
            deriver_identifier__in=(
                trove_db.ResourceIdentifier.objects
                .queryset_for_iri(deriver_iri)
            ),
        )
        .select_related('upriver_indexcard')
        .prefetch_related('upriver_indexcard__focus_identifier_set')
    )
    _by_card_iri = {}
    for _derived in _derived_indexcard_qs:
        _indexcard_iri = _derived.upriver_indexcard.get_iri()
        _by_card_iri[_indexcard_iri] = _describe_indexcard_derived(_indexcard_iri, _derived)
    return _by_card_iri


def _describe_indexcard_nonderived(
    indexcard_iri: str,
    indexcard_rdf: trove_db.IndexcardRdf,
) -> rdf.RdfGraph:
    _card_description = rdf.RdfGraph({
        indexcard_iri: {
            TROVE.resourceMetadata: {indexcard_rdf.as_quoted_graph()},
            DCTERMS.issued: {indexcard_rdf.indexcard.created.date()},
            DCTERMS.modified: {indexcard_rdf.modified.date()},
        },
    })
    for _identifier in indexcard_rdf.indexcard.focus_identifier_set.all():
        _iri = _identifier.as_iri()
        _card_description.add((indexcard_iri, FOAF.primaryTopic, _iri))
        _card_description.add((indexcard_iri, TROVE.focusIdentifier, literal(_iri)))
    return _card_description


def _describe_indexcard_derived(
    indexcard_iri: str,
    derived_indexcard: trove_db.DerivedIndexcard,
) -> rdf.RdfGraph:
    _card_description = rdf.RdfGraph({
        indexcard_iri: {
            TROVE.resourceMetadata: {derived_indexcard.as_rdf_literal()},
            DCTERMS.issued: {derived_indexcard.upriver_indexcard.created.date()},
            DCTERMS.modified: {derived_indexcard.modified.date()},
        },
    })
    for _identifier in derived_indexcard.upriver_indexcard.focus_identifier_set.all():
        _iri = _identifier.as_iri()
        _card_description.add((indexcard_iri, FOAF.primaryTopic, _iri))
        _card_description.add((indexcard_iri, TROVE.focusIdentifier, literal(_iri)))
    return _card_description


###
# local helpers

def _filter_as_blanknode(search_filter) -> frozenset:
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


def _osfmap_or_unknown_iri_as_json(iri: str):
    try:
        _twopledict = OSFMAP_THESAURUS[iri]
    except KeyError:
        return rdf.literal_json({'@id': iri})
    else:
        return _osfmap_json({iri: _twopledict}, focus_iri=iri)


def _valuesearch_result_as_json(result: ValuesearchResult) -> Literal:
    _value_twopledict = {
        RDF.type: set(result.value_type),
        FOAF.name: set(map(literal, result.name_text)),
        DCTERMS.title: set(map(literal, result.title_text)),
        RDFS.label: set(map(literal, result.label_text)),
    }
    return (
        _osfmap_json({result.value_iri: _value_twopledict}, result.value_iri)
        if result.value_iri
        else _osfmap_twople_json(_value_twopledict)
    )


def _valuesearch_result_as_indexcard_blanknode(result: ValuesearchResult) -> frozenset:
    return blanknode({
        RDF.type: {TROVE.Indexcard},
        TROVE.focusIdentifier: {literal(result.value_iri or result.value_value)},
        TROVE.resourceMetadata: {_valuesearch_result_as_json(result)},
    })


def _osfmap_json(tripledict, focus_iri):
    return rdf.literal_json(
        _RdfOsfmapJsonldRenderer().tripledict_as_nested_jsonld(tripledict, focus_iri)
    )


def _osfmap_twople_json(twopledict):
    return rdf.literal_json(
        _RdfOsfmapJsonldRenderer().twopledict_as_jsonld(twopledict)
    )


def _osfmap_path(property_path):
    return rdf.literal_json([
        osfmap_shorthand().compact_iri(_iri)
        for _iri in property_path
    ])


def _single_propertypath_twoples(property_path: tuple[str, ...]):
    yield (TROVE.propertyPathKey, literal(propertypath_key(property_path)))
    yield (TROVE.propertyPath, _propertypath_sequence(property_path))
    yield (TROVE.osfmapPropertyPath, _osfmap_path(property_path))


def _multi_propertypath_twoples(propertypath_set):
    yield (TROVE.propertyPathKey, literal(propertypath_set_key(propertypath_set)))
    for _path in propertypath_set:
        yield (TROVE.propertyPathSet, _propertypath_sequence(_path))


def _propertypath_sequence(property_path: tuple[str, ...]):
    _propertypath_metadata = []
    for _property_iri in property_path:
        try:
            _property_twopledict = OSFMAP_THESAURUS[_property_iri]
        except KeyError:
            _property_twopledict = {RDF.type: {RDF.Property}}  # giving benefit of the doubt
        _propertypath_metadata.append(_osfmap_json(
            {_property_iri: _property_twopledict},
            focus_iri=_property_iri,
        ))
    return sequence(_propertypath_metadata)


def _related_property_result(property_path: tuple[str, ...], count: int):
    return frozenset((
        (RDF.type, TROVE.RelatedPropertypath),
        (TROVE.cardsearchResultCount, count),
        (TROVE.suggestedFilterOperator, literal(trove_shorthand().compact_iri(
            suggested_filter_operator(property_path[-1]),
        ))),
        *_single_propertypath_twoples(property_path),
    ))


def _search_page_links(search_focus, search_params):
    _search_iri_split = urllib.parse.urlsplit(next(iter(search_focus.iris)))

    def _iri_with_cursor(page_cursor: PageCursor):
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


def _jsonapi_link(membername, iri):
    return frozenset((
        (RDF.type, JSONAPI_LINK_OBJECT),
        (JSONAPI_MEMBERNAME, literal(membername)),
        (RDF.value, iri),
    ))
