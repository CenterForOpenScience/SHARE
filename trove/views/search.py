import logging

from django import http
from django.views import View
from primitive_metadata import gather

from share.search import index_strategy
from trove import exceptions as trove_exceptions
from trove.trovesearch.search_params import (
    BaseTroveParams,
    CardsearchParams,
    ValuesearchParams,
)
from trove.trovesearch.trovesearch_gathering import trovesearch_by_indexstrategy
from trove.vocab.namespaces import TROVE, FOAF, DCTERMS
from trove.render import (
    DEFAULT_RENDERER_TYPE,
    get_renderer_type,
)
from ._responder import (
    make_http_error_response,
    make_http_response,
)


logger = logging.getLogger(__name__)


DEFAULT_INCLUDES_BY_TYPE = {
    TROVE.Cardsearch: {
        TROVE.searchResultPage,
        TROVE.relatedPropertyList,
    },
    TROVE.Valuesearch: {
        TROVE.searchResultPage,
    },
    TROVE.SearchResult: {
        TROVE.indexCard,
    },
}

DEFAULT_FIELDS_BY_TYPE = {
    TROVE.Indexcard: {
        TROVE.resourceMetadata,
        TROVE.focusIdentifier,
        DCTERMS.issued,
        DCTERMS.modified,
        FOAF.primaryTopic
    },
    TROVE.Cardsearch: {
        TROVE.totalResultCount,
        TROVE.cardSearchText,
        TROVE.cardSearchFilter,
    },
    TROVE.Valuesearch: {
        TROVE.propertyPath,
        TROVE.valueSearchText,
        TROVE.valueSearchFilter,
        TROVE.cardSearchText,
        TROVE.cardSearchFilter,
    },
}


class _BaseTrovesearchView(View):
    # expected on inheritors
    focus_type_iri: str
    params_dataclass: type[BaseTroveParams]

    def get(self, request):
        _url = request.build_absolute_uri()
        try:
            _renderer_type = get_renderer_type(request)
        except trove_exceptions.CannotRenderMediatype as _error:
            return make_http_error_response(
                error=_error,
                renderer=DEFAULT_RENDERER_TYPE(_url),
            )
        try:
            _search_gathering = self._start_gathering(
                search_params=self._parse_search_params(request),
                renderer_type=_renderer_type,
            )
            _focus = gather.Focus.new(_url, self.focus_type_iri)
            _search_gathering.ask(self._get_asktree(request), focus=_focus)
            _renderer = _renderer_type(_url, _search_gathering.leaf_a_record())
            return make_http_response(
                content_rendering=_renderer.render_document(),
                http_request=request,
            )
        except trove_exceptions.TroveError as _error:
            return make_http_error_response(
                error=_error,
                renderer=_renderer_type(_url),
            )

    def _parse_search_params(self, request: http.HttpRequest):
        return self.params_dataclass.from_querystring(
            request.META['QUERY_STRING'],
        )

    def _start_gathering(self, search_params, renderer_type) -> gather.Gathering:
        _specific_index = index_strategy.get_index_for_trovesearch(search_params)
        # TODO: 404 for unknown strategy
        return trovesearch_by_indexstrategy.new_gathering({
            'search_params': search_params,
            'specific_index': _specific_index,
            'deriver_iri': renderer_type.INDEXCARD_DERIVER_IRI,
        })

    def _get_asktree(self, request: http.HttpRequest):
        ...


class CardsearchView(_BaseTrovesearchView):
    focus_type_iri = TROVE.Cardsearch
    params_dataclass = CardsearchParams


class ValuesearchView(_BaseTrovesearchView):
    focus_type_iri = TROVE.Valuesearch
    params_dataclass = ValuesearchParams
