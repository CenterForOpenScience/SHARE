import logging

from django import http
from django.views import View
from gather import gathering

from share.search.index_strategy import IndexStrategy
from share.search.search_params import (
    CardsearchParams,
    ValuesearchParams,
)
from trove.vocab.namespaces import TROVE
from trove.trovesearch_gathering import trovesearch_by_indexstrategy
from trove.render import render_from_rdf, JSONAPI_MEDIATYPE


logger = logging.getLogger(__name__)


DEFAULT_CARDSEARCH_ASK = {
    TROVE.totalResultCount: None,
    TROVE.cardsearchText: None,
    TROVE.cardsearchFilter: None,
    TROVE.searchResultPage: {
        TROVE.indexCard: {
            TROVE.resourceMetadata,
        },
    },
}

DEFAULT_VALUESEARCH_ASK = {
    TROVE.propertyPath: None,
    TROVE.valuesearchText: None,
    TROVE.valuesearchFilter: None,
    TROVE.cardsearchText: None,
    TROVE.cardsearchFilter: None,
    TROVE.searchResultPage: {
        TROVE.indexCard: {
            TROVE.resourceMetadata,
        },
    },
}


class CardsearchView(View):
    def get(self, request):
        _search_iri, _search_gathering = _parse_request(request, CardsearchParams)
        _search_gathering.ask(
            DEFAULT_CARDSEARCH_ASK,  # TODO: build from `include`/`fields`
            focus=gathering.focus(_search_iri, TROVE.Cardsearch),
        )
        return http.HttpResponse(
            content=render_from_rdf(
                _search_gathering.leaf_a_record(),
                _search_iri,
                JSONAPI_MEDIATYPE,
            ),
            content_type=JSONAPI_MEDIATYPE,
        )


class ValuesearchView(View):
    def get(self, request):
        _search_iri, _search_gathering = _parse_request(request, ValuesearchParams)
        _search_gathering.ask(
            DEFAULT_VALUESEARCH_ASK,  # TODO: build from `include`/`fields`
            focus=gathering.focus(_search_iri, TROVE.Valuesearch),
        )
        return http.HttpResponse(
            content=render_from_rdf(
                _search_gathering.leaf_a_record(),
                _search_iri,
                JSONAPI_MEDIATYPE,
            ),
            content_type=JSONAPI_MEDIATYPE,
        )


###
# local helpers

def _parse_request(request: http.HttpRequest, search_params_dataclass):
    _search_iri = request.build_absolute_uri()
    _search_params = search_params_dataclass.from_querystring(
        request.META['QUERY_STRING'],
    )
    _specific_index = IndexStrategy.get_for_trove_search(_search_params.index_strategy_name)
    # TODO: 404 for unknown strategy
    _search_gathering = trovesearch_by_indexstrategy.new_gathering({
        'search_params': _search_params,
        'specific_index': _specific_index,
    })
    return (_search_iri, _search_gathering)
