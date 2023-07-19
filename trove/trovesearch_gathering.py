import json

import gather

from share.search.search_request import (
    CardsearchParams,
    PropertysearchParams,
    ValuesearchParams,
)
from trove import models as trove_db
from trove.vocab.iri_namespace import RDF
from trove.vocab.trove import TROVE, TROVE_API_VOCAB, trove_indexcard_namespace


TROVE_GATHERING_NORMS = gather.GatheringNorms(
    namestory=(
        gather.text('cardsearch', language_tag='en'),
        gather.text('search for "index cards" that describe resources', language_tag='en'),
    ),
    focustype_iris={
        TROVE.Indexcard,
        TROVE.Cardsearch,
        TROVE.Propertysearch,
        TROVE.Valuesearch,
    },
    vocabulary=TROVE_API_VOCAB,
)


trovesearch_by_indexstrategy = gather.GatheringOrganizer(
    namestory=(
        gather.text('trove search', language_tag='en'),
    ),
    norms=TROVE_GATHERING_NORMS,
    gatherer_kwargnames={'search_params', 'specific_index'},
)


@trovesearch_by_indexstrategy.gatherer(TROVE.cardsearchText)
def gather_cardsearch_text(focus, *, specific_index, search_params):
    yield (TROVE.cardsearchText, gather.text(search_params.cardsearch_text))


@trovesearch_by_indexstrategy.gatherer(TROVE.propertysearchText)
def gather_propertysearch_text(focus, *, specific_index, search_params):
    yield (TROVE.propertysearchText, gather.text(search_params.propertysearch_text))


@trovesearch_by_indexstrategy.gatherer(TROVE.valuesearchText)
def gather_valuesearch_text(focus, *, specific_index, search_params):
    yield (TROVE.valuesearchText, gather.text(search_params.valuesearch_text))


@trovesearch_by_indexstrategy.gatherer(TROVE.cardsearchFilter)
def gather_cardsearch_filter(focus, *, specific_index, search_params):
    for _filter in search_params.cardsearch_filter_set:
        yield (TROVE.cardsearchFilter, _filter_as_blanknode(_filter))


@trovesearch_by_indexstrategy.gatherer(TROVE.propertysearchFilter)
def gather_propertysearch_filter(focus, *, specific_index, search_params):
    for _filter in search_params.propertysearch_filter_set:
        yield (TROVE.propertysearchFilter, _filter_as_blanknode(_filter))


@trovesearch_by_indexstrategy.gatherer(TROVE.valuesearchFilter)
def gather_valuesearch_filter(focus, *, specific_index, search_params):
    for _filter in search_params.valuesearch_filter_set:
        yield (TROVE.valuesearchFilter, _filter_as_blanknode(_filter))


@trovesearch_by_indexstrategy.gatherer(
    TROVE.totalResultCount,
    TROVE.searchResult,
    focustype_iris={TROVE.Cardsearch},
)
def gather_cardsearch(focus, *, specific_index, search_params):
    assert isinstance(search_params, CardsearchParams)
    _cardsearch_resp = specific_index.pls_handle_cardsearch(search_params)
    # yield (TROVE.WOOP, gather.text(json.dumps(_cardsearch_resp), language_iri=RDF.JSON))
    yield (TROVE.totalResultCount, _cardsearch_resp.total_result_count)
    for _result in _cardsearch_resp.search_result_page:
        yield (_result.card_iri, RDF.type, TROVE.Indexcard)
        _text_evidence_twoples = (
            (TROVE.matchEvidence, frozenset((
                (RDF.type, TROVE.TextMatchEvidence),
                (TROVE.propertyPath, _evidence.property_path),
                (TROVE.matchingHighlight, _evidence.matching_highlight),
                (TROVE.indexCard, _evidence.card_iri),
            )))
            for _evidence in _result.text_match_evidence
        )
        yield (TROVE.searchResult, frozenset((
            (RDF.type, TROVE.SearchResult),
            (TROVE.indexCard, _result.card_iri),
            *_text_evidence_twoples,
        )))


@trovesearch_by_indexstrategy.gatherer(
    focustype_iris={TROVE.Propertysearch},
)
def gather_propertysearch(focus, *, specific_index, search_params):
    assert isinstance(search_params, PropertysearchParams)
    _propertysearch_resp = specific_index.pls_handle_propertysearch(search_params)
    yield (TROVE.totalResultCount, _propertysearch_resp.total_result_count)
    for _result in _propertysearch_resp.search_result_page:
        yield (_result.card_iri, RDF.type, TROVE.Indexcard)
        _text_evidence_twoples = (
            (TROVE.matchEvidence, frozenset((
                (RDF.type, TROVE.TextMatchEvidence),
                (TROVE.propertyPath, _evidence.property_path),
                (TROVE.matchingHighlight, _evidence.matching_highlight),
                (TROVE.card, _evidence.card_iri),
            )))
            for _evidence in _result.text_match_evidence
        )
        yield (TROVE.searchResult, frozenset((
            (RDF.type, TROVE.SearchResult),
            (TROVE.indexCard, _result.card_iri),
            *_text_evidence_twoples,
        )))


@trovesearch_by_indexstrategy.gatherer(
    focustype_iris={TROVE.Valuesearch},
)
def gather_valuesearch(focus, *, specific_index, search_params):
    assert isinstance(search_params, ValuesearchParams)
    _valuesearch_resp = specific_index.pls_handle_valuesearch(search_params)
    yield (TROVE.WOOP, gather.text(json.dumps(_valuesearch_resp), language_iri=RDF.JSON))
    return  # TODO
    yield (TROVE.totalResultCount, _valuesearch_resp.total_result_count)
    for _result in _valuesearch_resp.search_result_page:
        yield (_result.card_iri, RDF.type, TROVE.Indexcard)
        _text_evidence_twoples = (
            (TROVE.matchEvidence, frozenset((
                (RDF.type, TROVE.TextMatchEvidence),
                (TROVE.propertyPath, _evidence.property_path),
                (TROVE.matchingHighlight, _evidence.matching_highlight),
                (TROVE.card, _evidence.card_iri),
            )))
            for _evidence in _result.text_match_evidence
        )
        yield (TROVE.searchResult, frozenset((
            (RDF.type, TROVE.SearchResult),
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
    _indexcard_uuid = gather.IriNamespace.without_namespace(
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
        gather.text(_osfmap_indexcard.derived_text, language_iri=RDF.JSON)
    )


###
# local helpers

def _filter_as_blanknode(search_filter) -> frozenset:
    _filter_values = (
        (TROVE.filterValue, _value)
        for _value in search_filter.value_set
    )
    return frozenset((
        # property_path is a tuple, which becomes an rdf sequence
        (TROVE.propertyPath, search_filter.property_path),
        (TROVE.filterType, TROVE[search_filter.operator.value]),
        *_filter_values,
    ))
