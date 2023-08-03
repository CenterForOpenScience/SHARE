import dataclasses
import json
import logging
import urllib.parse

from gather import primitive_rdf, gathering

from share.search.search_request import (
    CardsearchParams,
    PropertysearchParams,
    ValuesearchParams,
    SearchFilter,
    PageParam,
)
from share.search.search_response import ValuesearchResult
from trove import models as trove_db
from trove.render.jsonld import RdfJsonldRenderer
from trove.vocab.namespaces import RDF, FOAF, DCTERMS, RDFS
from trove.vocab.osfmap import osfmap_labeler, OSFMAP_VOCAB, suggested_property_iris
from trove.vocab.trove import (
    TROVE,
    TROVE_API_VOCAB,
    trove_indexcard_namespace,
    JSONAPI_LINK_OBJECT,
    JSONAPI_MEMBERNAME,
)


logger = logging.getLogger(__name__)


TROVE_GATHERING_NORMS = gathering.GatheringNorms(
    namestory=(
        primitive_rdf.text('cardsearch', language_tag='en'),
        primitive_rdf.text('search for "index cards" that describe resources', language_tag='en'),
    ),
    focustype_iris={
        TROVE.Indexcard,
        TROVE.Cardsearch,
        TROVE.Propertysearch,
        TROVE.Valuesearch,
    },
    vocabulary=TROVE_API_VOCAB,
)


trovesearch_by_indexstrategy = gathering.GatheringOrganizer(
    namestory=(
        primitive_rdf.text('trove search', language_tag='en'),
    ),
    norms=TROVE_GATHERING_NORMS,
    gatherer_kwargnames={'search_params', 'specific_index'},
)


@trovesearch_by_indexstrategy.gatherer(TROVE.cardsearchText)
def gather_cardsearch_text(focus, *, specific_index, search_params):
    yield (TROVE.cardsearchText, primitive_rdf.text(search_params.cardsearch_text))


@trovesearch_by_indexstrategy.gatherer(TROVE.propertysearchText)
def gather_propertysearch_text(focus, *, specific_index, search_params):
    yield (TROVE.propertysearchText, primitive_rdf.text(search_params.propertysearch_text))


@trovesearch_by_indexstrategy.gatherer(TROVE.valuesearchText)
def gather_valuesearch_text(focus, *, specific_index, search_params):
    yield (TROVE.valuesearchText, primitive_rdf.text(search_params.valuesearch_text))


@trovesearch_by_indexstrategy.gatherer(TROVE.valuesearchPropertyPath)
def gather_valuesearch_propertypath(focus, *, specific_index, search_params):
    yield (TROVE.valuesearchPropertyPath, _literal_json(search_params.valuesearch_property_path))
    yield (TROVE.osfmapPropertyPath, _osfmap_path(search_params.valuesearch_property_path))


@trovesearch_by_indexstrategy.gatherer(TROVE.propertysearchFilter)
def gather_propertysearch_filter(focus, *, specific_index, search_params):
    for _filter in search_params.propertysearch_filter_set:
        yield (TROVE.propertysearchFilter, _filter_as_blanknode(_filter, {}))


@trovesearch_by_indexstrategy.gatherer(TROVE.valuesearchFilter)
def gather_valuesearch_filter(focus, *, specific_index, search_params):
    for _filter in search_params.valuesearch_filter_set:
        yield (TROVE.valuesearchFilter, _filter_as_blanknode(_filter, {}))


@trovesearch_by_indexstrategy.gatherer(
    TROVE.totalResultCount,
    TROVE.searchResultPage,
    TROVE.cardsearchFilter,
    focustype_iris={TROVE.Cardsearch},
)
def gather_cardsearch(focus, *, specific_index, search_params):
    assert isinstance(search_params, CardsearchParams)
    _cardsearch_resp = specific_index.pls_handle_cardsearch(search_params)
    yield (TROVE.totalResultCount, _cardsearch_resp.total_result_count)
    _result_page = []
    for _result in _cardsearch_resp.search_result_page:
        yield (_result.card_iri, RDF.type, TROVE.Indexcard)
        _text_evidence_twoples = (
            (TROVE.matchEvidence, frozenset((
                (RDF.type, TROVE.TextMatchEvidence),
                (TROVE.propertyPath, _literal_json(_evidence.property_path)),
                (TROVE.osfmapPropertyPath, _osfmap_path(_evidence.property_path)),
                (TROVE.matchingHighlight, _evidence.matching_highlight),
                (TROVE.indexCard, _evidence.card_iri),
            )))
            for _evidence in _result.text_match_evidence
        )
        _result_page.append(frozenset((
            (RDF.type, TROVE.SearchResult),
            (TROVE.indexCard, _result.card_iri),
            *_text_evidence_twoples,
        )))
    yield (TROVE.searchResultPage, primitive_rdf.sequence(_result_page))
    yield (TROVE.relatedProperty, _related_properties(search_params))
    yield from _search_page_links(focus, search_params, _cardsearch_resp)
    _valueinfo_by_iri = {}
    for _filtervalue in _cardsearch_resp.filtervalue_info:
        _value_info = _value_info_json(_filtervalue)
        _valueinfo_by_iri[_filtervalue.value_iri] = _value_info
    for _filter in search_params.cardsearch_filter_set:
        yield (TROVE.cardsearchFilter, _filter_as_blanknode(_filter, _valueinfo_by_iri))


@trovesearch_by_indexstrategy.gatherer(
    focustype_iris={TROVE.Valuesearch},
)
def gather_valuesearch(focus, *, specific_index, search_params):
    assert isinstance(search_params, ValuesearchParams)
    _valuesearch_resp = specific_index.pls_handle_valuesearch(search_params)
    _result_page = []
    for _result in _valuesearch_resp.search_result_page:
        _result_page.append(primitive_rdf.freeze_blanknode({
            RDF.type: {TROVE.SearchResult},
            TROVE.cardsearchResultCount: {_result.match_count},
            TROVE.indexCard: {_valuesearch_result_as_indexcard_blanknode(_result)},
        }))
    yield (TROVE.totalResultCount, _valuesearch_resp.total_result_count)
    yield (TROVE.searchResultPage, primitive_rdf.sequence(_result_page))
    yield from _search_page_links(focus, search_params, _valuesearch_resp)


@trovesearch_by_indexstrategy.gatherer(
    focustype_iris={TROVE.Propertysearch},
)
def gather_propertysearch(focus, *, specific_index, search_params):
    assert isinstance(search_params, PropertysearchParams)
    _propertysearch_resp = specific_index.pls_handle_propertysearch(search_params)
    yield (TROVE.WOOP, _literal_json(_propertysearch_resp, indent=2))
    return
    yield (TROVE.totalResultCount, _propertysearch_resp.total_result_count)
    for _result in _propertysearch_resp.search_result_page:
        yield (_result.card_iri, RDF.type, TROVE.Indexcard)
        _text_evidence_twoples = (
            (TROVE.matchEvidence, frozenset((
                (RDF.type, TROVE.TextMatchEvidence),
                (TROVE.propertyPath, _literal_json(_evidence.property_path)),
                (TROVE.osfmapPropertyPath, _osfmap_path(_evidence.property_path)),
                (TROVE.matchingHighlight, _evidence.matching_highlight),
                (TROVE.card, _evidence.card_iri),
            )))
            for _evidence in _result.text_match_evidence
        )
        yield (TROVE.searchResultPage, frozenset((
            (RDF.type, TROVE.PropertysearchResult),
            (TROVE.indexCard, _result.card_iri),
            *_text_evidence_twoples,
        )))


@trovesearch_by_indexstrategy.gatherer(
    focustype_iris={TROVE.Indexcard},
)
def gather_card(focus, **kwargs):
    # TODO: batch gatherer -- load all cards in one query
    _indexcard_namespace = trove_indexcard_namespace()
    try:
        _indexcard_iri = next(
            _iri
            for _iri in focus.iris
            if _iri in _indexcard_namespace
        )
    except StopIteration:
        raise ValueError(f'could not find indexcard iri in {focus.iris} (looking for {_indexcard_namespace})')
    _indexcard_uuid = primitive_rdf.IriNamespace.without_namespace(
        _indexcard_iri,
        namespace=_indexcard_namespace,
    )
    _osfmap_indexcard = (
        trove_db.DerivedIndexcard.objects
        .filter(
            upriver_indexcard__uuid=_indexcard_uuid,
            deriver_identifier__in=(
                trove_db.ResourceIdentifier.objects
                .queryset_for_iri(TROVE['derive/osfmap_json'])
                # TODO: choose deriver by queryparam/gatherer-kwarg
            ),
        )
        .select_related('upriver_indexcard')
        .prefetch_related('upriver_indexcard__focus_identifier_set')
        .get()
    )
    for _identifier in _osfmap_indexcard.upriver_indexcard.focus_identifier_set.all():
        yield (TROVE.resourceIdentifier, _identifier.as_iri())
    yield (
        TROVE.resourceMetadata,
        primitive_rdf.text(_osfmap_indexcard.derived_text, language_iri=RDF.JSON)
    )


###
# local helpers

def _filter_as_blanknode(search_filter, valueinfo_by_iri) -> frozenset:
    _filtervalue_twoples = []
    for _value in search_filter.value_set:
        _valueinfo = (
            valueinfo_by_iri.get(_value)
            or _literal_json({'@id': _value})
        )
        _filtervalue_twoples.append((TROVE.filterValue, _valueinfo))
    return frozenset((
        (TROVE.propertyPath, _literal_json(search_filter.property_path)),
        (TROVE.osfmapPropertyPath, _osfmap_path(search_filter.property_path)),
        (TROVE.filterType, TROVE[search_filter.operator.value]),
        *_filtervalue_twoples,
    ))


def _value_info_json(result: ValuesearchResult) -> primitive_rdf.Text:
    _value_twopledict = {
        RDF.type: set(result.value_type),
        FOAF.name: set(map(primitive_rdf.text, result.name_text)),
        DCTERMS.title: set(map(primitive_rdf.text, result.title_text)),
        RDFS.label: set(map(primitive_rdf.text, result.label_text)),
    }
    try:
        _label = osfmap_labeler.label_for_iri(result.value_iri)
    except KeyError:
        pass
    else:
        _value_twopledict[RDFS.label].add(primitive_rdf.text(_label))
    return _osfmap_json({result.value_iri: _value_twopledict}, result.value_iri)


def _valuesearch_result_as_indexcard_blanknode(result: ValuesearchResult) -> frozenset:
    return primitive_rdf.freeze_blanknode({
        RDF.type: {TROVE.Indexcard},
        TROVE.resourceIdentifier: {primitive_rdf.text(result.value_iri)},
        TROVE.resourceMetadata: {_value_info_json(result)},
    })


def _osfmap_json(tripledict, focus_iri):
    return _literal_json(
        RdfJsonldRenderer(OSFMAP_VOCAB, osfmap_labeler).tripledict_as_nested_jsonld(
            tripledict,
            focus_iri,
        )
    )


def _literal_json(jsonable_obj, **dumps_kwargs):
    return primitive_rdf.text(
        json.dumps(jsonable_obj, **dumps_kwargs),
        language_iri=RDF.JSON,
    )


def _osfmap_path(property_path):
    return _literal_json([
        osfmap_labeler.get_label_or_iri(_iri)
        for _iri in property_path
    ])


def _related_properties(search_params):
    # hard-coded for osf.io search pages, static list per type
    # TODO: replace with some dynamism, maybe a 'significant_terms' aggregation
    _type_iris = set()
    for _filter in search_params.cardsearch_filter_set:
        if _filter.property_path == (RDF.type,):
            if _filter.operator == SearchFilter.FilterOperator.ANY_OF:
                _type_iris.update(_filter.value_set)
            if _filter.operator == SearchFilter.FilterOperator.NONE_OF:
                _type_iris.difference_update(_filter.value_set)
    _property_iris = suggested_property_iris(_type_iris)
    return primitive_rdf.sequence(
        _static_property_indexcard(_property_iri)
        for _property_iri in _property_iris
    )


def _static_property_indexcard(osfmap_property_iri):
    _property_metadata = {
        osfmap_property_iri: OSFMAP_VOCAB[osfmap_property_iri]
    }
    return primitive_rdf.freeze_blanknode({
        RDF.type: {TROVE.Indexcard},
        TROVE.resourceIdentifier: {primitive_rdf.text(osfmap_property_iri)},
        TROVE.resourceMetadata: {
            _osfmap_json(_property_metadata, osfmap_property_iri),
        },
    })


def _search_page_links(search_focus, search_params, search_response):
    _search_iri_split = urllib.parse.urlsplit(next(iter(search_focus.iris)))

    def _iri_with_page_param(page_param: PageParam):
        return urllib.parse.urlunsplit((
            _search_iri_split.scheme,
            _search_iri_split.netloc,
            _search_iri_split.path,
            dataclasses.replace(search_params, page=page_param).to_querystring(),
            _search_iri_split.fragment,
        ))

    if search_response.first_page_cursor:
        yield (TROVE.searchResultPage, _jsonapi_link('first', _iri_with_page_param(
            PageParam(cursor=search_response.first_page_cursor),
        )))
    if search_response.next_page_cursor:
        yield (TROVE.searchResultPage, _jsonapi_link('next', _iri_with_page_param(
            PageParam(cursor=search_response.next_page_cursor),
        )))
    if search_response.prev_page_cursor:
        yield (TROVE.searchResultPage, _jsonapi_link('prev', _iri_with_page_param(
            PageParam(cursor=search_response.prev_page_cursor),
        )))


def _jsonapi_link(membername, iri):
    return frozenset((
        (RDF.type, JSONAPI_LINK_OBJECT),
        (JSONAPI_MEMBERNAME, primitive_rdf.text(membername)),
        (RDF.value, iri),
    ))
