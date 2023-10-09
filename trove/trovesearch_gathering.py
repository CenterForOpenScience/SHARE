import dataclasses
import json
import logging
import urllib.parse

from gather import primitive_rdf, gathering

from share.search.search_params import (
    CardsearchParams,
    ValuesearchParams,
    PageParam,
    propertypath_key,
    propertypath_set_key,
)
from share.search.search_response import ValuesearchResult
from trove import models as trove_db
from trove.render.jsonld import RdfJsonldRenderer
from trove.vocab.namespaces import RDF, FOAF, DCTERMS, RDFS
from trove.vocab.osfmap import osfmap_labeler, OSFMAP_VOCAB, suggested_filter_operator
from trove.vocab.trove import (
    TROVE,
    TROVE_API_VOCAB,
    trove_indexcard_namespace,
    trove_labeler,
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


# TODO: per-field text search in rdf
# @trovesearch_by_indexstrategy.gatherer(TROVE.cardsearchText)
# def gather_cardsearch_text(focus, *, specific_index, search_params):
#     yield (TROVE.cardsearchText, primitive_rdf.text(search_params.cardsearch_text))
#
#
# @trovesearch_by_indexstrategy.gatherer(TROVE.valuesearchText)
# def gather_valuesearch_text(focus, *, specific_index, search_params):
#     yield (TROVE.valuesearchText, primitive_rdf.text(search_params.valuesearch_text))


@trovesearch_by_indexstrategy.gatherer(TROVE.propertyPath, focustype_iris={TROVE.Valuesearch})
def gather_valuesearch_propertypath(focus, *, specific_index, search_params):
    yield from _multi_propertypath_twoples(search_params.valuesearch_propertypath_set)


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
    # defer to the IndexStrategy implementation to do the search
    _cardsearch_resp = specific_index.pls_handle_cardsearch(search_params)
    # resulting index-cards
    yield (TROVE.totalResultCount, _cardsearch_resp.total_result_count)
    _result_page = []
    for _result in _cardsearch_resp.search_result_page:
        yield (_result.card_iri, RDF.type, TROVE.Indexcard)
        _text_evidence_twoples = (
            (TROVE.matchEvidence, frozenset((
                (RDF.type, TROVE.TextMatchEvidence),
                (TROVE.matchingHighlight, _evidence.matching_highlight),
                (TROVE.indexCard, _evidence.card_iri),
                *_single_propertypath_twoples(_evidence.property_path),
            )))
            for _evidence in _result.text_match_evidence
        )
        _result_page.append(frozenset((
            (RDF.type, TROVE.SearchResult),
            (TROVE.indexCard, _result.card_iri),
            *_text_evidence_twoples,
        )))
    yield (TROVE.searchResultPage, primitive_rdf.sequence(_result_page))
    # links to more pages of results
    yield from _search_page_links(focus, search_params, _cardsearch_resp)
    # info about related properties (for refining/filtering further)
    _prop_usage_counts = {
        _prop_result.property_path: _prop_result.usage_count
        for _prop_result in _cardsearch_resp.related_propertypath_results
    }
    _relatedproperty_list = [
        _related_property_result(_propertypath, _prop_usage_counts.get(_propertypath, 0))
        for _propertypath in search_params.related_property_paths
    ]
    yield (TROVE.relatedPropertyList, primitive_rdf.sequence(_relatedproperty_list))
    # filter-values from search params, with any additional info
    _valueinfo_by_iri = {}
    for _filtervalue in _cardsearch_resp.filtervalue_info:
        _value_info = _valuesearch_result_as_json(_filtervalue)
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
    _filter_twoples = [
        (TROVE.filterType, search_filter.operator.value),
        *_multi_propertypath_twoples(search_filter.propertypath_set),
    ]
    if not search_filter.operator.is_valueless_operator():
        for _value in search_filter.value_set:
            if search_filter.operator.is_iri_operator():
                _valueinfo = (
                    valueinfo_by_iri.get(_value)
                    or _osfmap_or_unknown_iri_as_json(_value)
                )
            else:
                _valueinfo = _literal_json({'@value': _value})
            _filter_twoples.append((TROVE.filterValue, _valueinfo))
    return frozenset(_filter_twoples)


def _osfmap_or_unknown_iri_as_json(iri: str):
    try:
        _twopledict = OSFMAP_VOCAB[iri]
    except KeyError:
        return _literal_json({'@id': iri})
    else:
        return _osfmap_json({iri: _twopledict}, focus_iri=iri)


def _valuesearch_result_as_json(result: ValuesearchResult) -> primitive_rdf.Text:
    _value_twopledict = {
        RDF.type: set(result.value_type),
        FOAF.name: set(map(primitive_rdf.text, result.name_text)),
        DCTERMS.title: set(map(primitive_rdf.text, result.title_text)),
        RDFS.label: set(map(primitive_rdf.text, result.label_text)),
    }
    return (
        _osfmap_json({result.value_iri: _value_twopledict}, result.value_iri)
        if result.value_iri
        else _osfmap_twople_json(_value_twopledict)
    )


def _valuesearch_result_as_indexcard_blanknode(result: ValuesearchResult) -> frozenset:
    return primitive_rdf.freeze_blanknode({
        RDF.type: {TROVE.Indexcard},
        TROVE.resourceIdentifier: {primitive_rdf.text(result.value_iri or result.value_value)},
        TROVE.resourceMetadata: {_valuesearch_result_as_json(result)},
    })


def _osfmap_json(tripledict, focus_iri):
    return _literal_json(
        RdfJsonldRenderer(OSFMAP_VOCAB, osfmap_labeler).tripledict_as_nested_jsonld(
            tripledict,
            focus_iri,
        )
    )


def _osfmap_twople_json(twopledict):
    return _literal_json(
        RdfJsonldRenderer(OSFMAP_VOCAB, osfmap_labeler).twopledict_as_jsonld(twopledict),
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


def _single_propertypath_twoples(property_path: tuple[str, ...]):
    yield (TROVE.propertyPathKey, primitive_rdf.text(propertypath_key(property_path)))
    yield (TROVE.propertyPath, _propertypath_sequence(property_path))
    yield (TROVE.osfmapPropertyPath, _osfmap_path(property_path))


def _multi_propertypath_twoples(propertypath_set):
    yield (TROVE.propertyPathKey, primitive_rdf.text(propertypath_set_key(propertypath_set)))
    for _path in propertypath_set:
        yield (TROVE.propertyPathSet, _propertypath_sequence(_path))


def _propertypath_sequence(property_path: tuple[str, ...]):
    _propertypath_metadata = []
    for _property_iri in property_path:
        try:
            _property_twopledict = OSFMAP_VOCAB[_property_iri]
        except KeyError:
            _property_twopledict = {RDF.type: {RDF.Property}}  # giving benefit of the doubt
        _propertypath_metadata.append(_osfmap_json(
            {_property_iri: _property_twopledict},
            focus_iri=_property_iri,
        ))
    return primitive_rdf.sequence(_propertypath_metadata)


def _related_property_result(property_path: tuple[str, ...], count: int):
    return frozenset((
        (RDF.type, TROVE.RelatedPropertypath),
        (TROVE.cardsearchResultCount, count),
        (TROVE.suggestedFilterOperator, trove_labeler.label_for_iri(
            suggested_filter_operator(property_path[-1]),
        )),
        *_single_propertypath_twoples(property_path),
    ))


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
