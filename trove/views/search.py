import logging

from django import http
from django.views import View
from primitive_metadata import gather

from share.search import index_strategy
from trove import exceptions as trove_exceptions
from trove.trovesearch.search_params import (
    CardsearchParams,
    ValuesearchParams,
)
from trove.trovesearch.trovesearch_gathering import trovesearch_by_indexstrategy
from trove.vocab.namespaces import TROVE
from trove.render import get_renderer


logger = logging.getLogger(__name__)


DEFAULT_CARDSEARCH_ASK = {
    TROVE.totalResultCount: None,
    TROVE.cardSearchText: None,
    TROVE.cardSearchFilter: None,
    TROVE.searchResultPage: {
        TROVE.indexCard: {
            TROVE.resourceMetadata,
        },
    },
}

DEFAULT_VALUESEARCH_ASK = {
    TROVE.propertyPath: None,
    TROVE.valueSearchText: None,
    TROVE.valueSearchFilter: None,
    TROVE.cardSearchText: None,
    TROVE.cardSearchFilter: None,
    TROVE.searchResultPage: {
        TROVE.indexCard: {
            TROVE.resourceMetadata,
        },
    },
}


class CardsearchView(View):
    def get(self, request):
        _renderer = get_renderer(request)
        try:
            _search_iri, _search_gathering = _parse_request(request, _renderer, CardsearchParams)
            _search_gathering.ask(
                DEFAULT_CARDSEARCH_ASK,  # TODO: build from `include`/`fields`
                focus=gather.Focus.new(_search_iri, TROVE.Cardsearch),
            )
            return _renderer.render_response(_search_gathering.leaf_a_record(), _search_iri)
        except trove_exceptions.TroveError as _error:
            return _renderer.render_error_response(_error)


class ValuesearchView(View):
    def get(self, request):
        _renderer = get_renderer(request)
        try:
            _search_iri, _search_gathering = _parse_request(request, _renderer, ValuesearchParams)
            _search_gathering.ask(
                DEFAULT_VALUESEARCH_ASK,  # TODO: build from `include`/`fields`
                focus=gather.Focus.new(_search_iri, TROVE.Valuesearch),
            )
            return _renderer.render_response(_search_gathering.leaf_a_record(), _search_iri)
        except trove_exceptions.TroveError as _error:
            return _renderer.render_error_response(_error)


###
# local helpers

def _parse_request(request: http.HttpRequest, renderer, search_params_dataclass):
    _search_iri = request.build_absolute_uri()
    _search_params = search_params_dataclass.from_querystring(
        request.META['QUERY_STRING'],
    )
    _specific_index = index_strategy.get_index_for_trovesearch(_search_params)
    # TODO: 404 for unknown strategy
    _search_gathering = trovesearch_by_indexstrategy.new_gathering({
        'search_params': _search_params,
        'specific_index': _specific_index,
        'deriver_iri': renderer.INDEXCARD_DERIVER_IRI,
    })
    return (_search_iri, _search_gathering)
