import abc
import logging
from typing import Callable

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
from trove.trovesearch.trovesearch_gathering import (
    trovesearch_by_indexstrategy,
    CardsearchFocus,
    ValuesearchFocus,
)
from trove.render import (
    DEFAULT_RENDERER_TYPE,
    get_renderer_type,
)
from ._responder import (
    make_http_error_response,
    make_http_response,
)


logger = logging.getLogger(__name__)


_TrovesearchHandler = Callable[[BaseTroveParams], BasicSearchHandle]


class _BaseTrovesearchView(View, abc.ABC):
    # expected on inheritors
    focus_type: type[gather.Focus]
    params_dataclass: type[CardsearchParams]

    def get(self, request):
        try:
            _renderer_type = get_renderer_type(request)
        except trove_exceptions.CannotRenderMediatype as _error:
            return make_http_error_response(
                error=_error,
                renderer_type=DEFAULT_RENDERER_TYPE,
            )
        try:
            _url = request.build_absolute_uri()
            _search_gathering = self._start_gathering(renderer_type=_renderer_type)
            _search_params = self._parse_search_params(request)
            _specific_index = index_strategy.get_index_for_trovesearch(_search_params)
            _focus = self.focus_type.new(
                iris=_url,
                search_params=_search_params,
                search_handle=self.get_search_handle(_specific_index, _search_params),
            )
            if _renderer_type.PASSIVE_RENDER:
                # fill the gathering's cache with requested info
                _search_gathering.ask(_search_params.include, focus=_focus)
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

    def _parse_search_params(self, request: http.HttpRequest) -> CardsearchParams:
        return self.params_dataclass.from_querystring(
            request.META['QUERY_STRING'],
        )

    def _start_gathering(self, renderer_type) -> gather.Gathering:
        # TODO: 404 for unknown strategy
        return trovesearch_by_indexstrategy.new_gathering({
            'deriver_iri': renderer_type.INDEXCARD_DERIVER_IRI,
        })

    def get_search_handle(self, specific_index, search_params) -> BasicSearchHandle:
        return self._get_wrapped_handler(specific_index)(search_params)

    def get_search_handler(
        self,
        specific_index: index_strategy.IndexStrategy.SpecificIndex,
    ) -> _TrovesearchHandler:
        raise NotImplementedError

    def _get_wrapped_handler(self, specific_index):
        _raw_handler = self.get_search_handler(specific_index)

        def _wrapped_handler(search_params):
            _handle = _raw_handler(search_params)
            _handle.handler = _wrapped_handler
            return _handle
        return _wrapped_handler


class CardsearchView(_BaseTrovesearchView):
    focus_type = CardsearchFocus
    params_dataclass = CardsearchParams

    def get_search_handler(self, specific_index):
        return specific_index.pls_handle_cardsearch


class ValuesearchView(_BaseTrovesearchView):
    focus_type = ValuesearchFocus
    params_dataclass = ValuesearchParams

    def get_search_handler(self, specific_index):
        return specific_index.pls_handle_valuesearch
