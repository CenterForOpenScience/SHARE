import abc
import logging

from django import http
from django.views import View
from primitive_metadata import gather

from share.search import index_strategy
from trove import exceptions as trove_exceptions
from trove.trovesearch.search_handle import BasicSearchHandle
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


class _BaseTrovesearchView(View, abc.ABC):
    # expected on inheritors
    focus_type_iri: str
    params_dataclass: type[BaseTroveParams]

    def get(self, request):
        try:
            _renderer_type = get_renderer_type(request)
        except trove_exceptions.CannotRenderMediatype as _error:
            return make_http_error_response(
                error=_error,
                renderer_type=DEFAULT_RENDERER_TYPE,
            )
        try:
            _search_gathering = self._start_gathering(
                search_params=self._parse_search_params(request),
                renderer_type=_renderer_type,
            )
            _url = request.build_absolute_uri()
            _focus = gather.Focus.new(_url, self.focus_type_iri)
            # fill the gathering's cache with requested info
            self._gather_by_request(_search_gathering, _focus, request)
            # take gathered data into a response
            _renderer = _renderer_type(_focus, _search_gathering)
            return make_http_response(
                content_rendering=_renderer.render_document(),
                http_request=request,
            )
        except trove_exceptions.TroveError as _error:
            return make_http_error_response(
                error=_error,
                renderer_type=_renderer_type,
            )

    def _parse_search_params(self, request: http.HttpRequest) -> BaseTroveParams:
        return self.params_dataclass.from_querystring(
            request.META['QUERY_STRING'],
        )

    def _start_gathering(self, search_params: BaseTroveParams, renderer_type) -> gather.Gathering:
        _specific_index = index_strategy.get_index_for_trovesearch(search_params)
        # TODO: 404 for unknown strategy
        return trovesearch_by_indexstrategy.new_gathering({
            'search_params': search_params,
            'search_handle': self._get_search_handle(_specific_index),
            'specific_index': _specific_index,
            'deriver_iri': renderer_type.INDEXCARD_DERIVER_IRI,
        })

    def _gather_by_request(self, gathering, focus, request) -> None:
        gathering.ask(self._get_asktree(request), focus=focus)

    def _get_asktree(self, request: http.HttpRequest):
        ...

    def _get_gathering_kwargs(
        self,
        specific_index: index_strategy.IndexStrategy.SpecificIndex,
    ) -> BasicSearchHandle:
        raise NotImplementedError


class CardsearchView(_BaseTrovesearchView):
    focus_type_iri = TROVE.Cardsearch
    params_dataclass = CardsearchParams

    def _get_search_handle(self, specific_index, search_params) -> BasicSearchHandle:
        return specific_index.pls_handle_cardsearch(search_params)


class ValuesearchView(_BaseTrovesearchView):
    focus_type_iri = TROVE.Valuesearch
    params_dataclass = ValuesearchParams

    def _get_search_handle(self, specific_index, search_params) -> BasicSearchHandle:
        return specific_index.pls_handle_valuesearch(search_params)
