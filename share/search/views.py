import logging

import gather
from django import http
from django.views import View

from share.schema.osfmap import OSFMAP_VOCAB
from share.search import exceptions
from share.search.index_strategy import IndexStrategy
from share.search.search_request import (
    CardsearchParams,
    PropertysearchParams,
    ValuesearchParams,
)
from share.search.trovesearch_gathering import (
    TROVE,
    TROVESEARCH_VOCAB,
    trovesearch_by_indexstrategy,
)
from share.search.rdf_as_jsonapi import RdfAsJsonapi


logger = logging.getLogger(__name__)


_TROVESEARCH_OSFMAP_VOCAB = {
    **TROVESEARCH_VOCAB,
    **OSFMAP_VOCAB,
}
if __debug__:
    if len(_TROVESEARCH_OSFMAP_VOCAB) != (len(TROVESEARCH_VOCAB) + len(OSFMAP_VOCAB)):
        _duplicate_keys = set(TROVESEARCH_VOCAB).intersection(OSFMAP_VOCAB)
        raise ValueError(f'vocab collision! duplicate keys: {_duplicate_keys}')


DEFAULT_CARDSEARCH_ASK = {
    TROVE.totalResultCount: None,
    TROVE.cardsearchText: None,
    TROVE.cardsearchFilter: None,
    TROVE.searchResult: {
        TROVE.indexCard: {
            TROVE.resourceMetadata,
        },
    },
}

DEFAULT_PROPERTYSEARCH_ASK = {
    TROVE.totalResultCount: None,
    TROVE.propertysearchText: None,
    TROVE.propertysearchFilter: None,
    TROVE.cardsearchText: None,
    TROVE.cardsearchFilter: None,
    TROVE.searchResult: {
        TROVE.indexCard: {
            TROVE.resourceMetadata,
        },
    },
}

DEFAULT_VALUESEARCH_ASK = {
    TROVE.totalResultCount: None,
    TROVE.valuesearchText: None,
    TROVE.valuesearchFilter: None,
    TROVE.cardsearchText: None,
    TROVE.cardsearchFilter: None,
    TROVE.searchResult: {
        TROVE.indexCard: {
            TROVE.resourceMetadata,
        },
    },
}


class CardsearchView(View):
    def get(self, request):
        _search_iri, _search_gathering = _parse_request(request, CardsearchParams)
        _search_gathering.ask(
            gather.focus(_search_iri, TROVE.Cardsearch),
            DEFAULT_CARDSEARCH_ASK,  # TODO: build from `include`/`fields`
        )
        return _search_response(_search_gathering.leaf_a_record(), _search_iri)


class PropertysearchView(View):
    def get(self, request):
        _search_iri, _search_gathering = _parse_request(request, PropertysearchParams)
        _search_gathering.ask(
            gather.focus(_search_iri, TROVE.Propertysearch),
            DEFAULT_PROPERTYSEARCH_ASK,  # TODO: build from `include`/`fields`
        )
        return _search_response(_search_gathering.leaf_a_record(), _search_iri)


class ValuesearchView(View):
    def get(self, request):
        _search_iri, _search_gathering = _parse_request(request, ValuesearchParams)
        _search_gathering.ask(
            gather.focus(_search_iri, TROVE.Valuesearch),
            DEFAULT_VALUESEARCH_ASK,  # TODO: build from `include`/`fields`
        )
        return _search_response(_search_gathering.leaf_a_record(), _search_iri)


###
# local helpers

def _parse_request(request: http.HttpRequest, search_params_dataclass):
    _search_iri = request.build_absolute_uri()
    _search_params = search_params_dataclass.from_querystring(
        request.META['QUERY_STRING'],
    )
    try:
        _specific_index = IndexStrategy.get_for_searching(
            _search_params.index_strategy_name,
            with_default_fallback=True,
        )
    except exceptions.IndexStrategyError as error:
        raise Exception('TODO: 404') from error
    _search_gathering = trovesearch_by_indexstrategy.new_gathering({
        'search_params': _search_params,
        'specific_index': _specific_index,
    })
    return (_search_iri, _search_gathering)


def _search_response(response_data: gather.RdfTripleDictionary, search_iri: str):
    _as_jsonapi = RdfAsJsonapi(response_data, _TROVESEARCH_OSFMAP_VOCAB)
    return http.JsonResponse(
        _as_jsonapi.jsonapi_datum_document(search_iri),
        json_dumps_params={'indent': 2},
    )
