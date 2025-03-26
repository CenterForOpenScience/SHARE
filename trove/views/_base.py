__all__ = ('BaseTroveView',)

import abc
from collections.abc import Container
from typing import ClassVar

from django import http as djhttp
from django.views import View
from primitive_metadata import gather

from trove import exceptions as trove_exceptions
from trove.vocab.namespaces import RDFS, TROVE
from trove.util.queryparams import BaseTroveParams
from trove.render import (
    BaseRenderer,
    DEFAULT_RENDERER_TYPE,
    get_renderer_type,
)
from ._gather_ask import ask_gathering_from_params
from ._responder import (
    make_http_error_response,
    make_http_response,
)


class BaseTroveView(View, abc.ABC):
    # ClassVars expected on inheritors:
    gathering_organizer: ClassVar[gather.GatheringOrganizer]
    params_type: ClassVar[type[BaseTroveParams]] = BaseTroveParams
    focus_type_iris: ClassVar[Container[str]] = (RDFS.Resource,)

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
            _params = self._parse_params(request)
            _renderer = self._gather_to_renderer(_url, _params, _renderer_type)
            return make_http_response(
                content_rendering=_renderer.render_document(),
                http_request=request,
            )
        except trove_exceptions.TroveError as _error:
            return make_http_error_response(
                error=_error,
                renderer_type=_renderer_type,
            )

    def _gather_to_renderer(self, url, params, renderer_type: type[BaseRenderer]) -> BaseRenderer:
        _focus = self._build_focus(url, params)
        _gathering = self._build_gathering(params, renderer_type)
        if renderer_type.PASSIVE_RENDER:
            ask_gathering_from_params(_gathering, params, _focus)
        return renderer_type(_focus, _gathering)

    def _parse_params(self, request: djhttp.HttpRequest):
        return self.params_type.from_querystring(request.META['QUERY_STRING'])

    def _build_focus(self, url, params):
        return gather.Focus(url, self.focus_type_iri)

    def _build_gathering(self, params, renderer_type: type[BaseRenderer]) -> gather.Gathering:
        return self.gathering_organizer.new_gathering(
            self._get_gatherer_kwargs(params, renderer_type),
        )

    def _get_gatherer_kwargs(self, params, renderer_type):
        _kwargs = {}
        _deriver_kw = _get_param_keyword(TROVE.deriverIRI, self.organizer)
        if _deriver_kw:
            _kwargs[_deriver_kw] = renderer_type.INDEXCARD_DERIVER_IRI
        return _kwargs


def _get_param_keyword(param_iri: str, organizer: gather.GatheringOrganizer) -> str | None:
    if param_iri in organizer.norms.param_iris:
        for (_k, _v) in organizer.gatherer_params.items():
            if _v == param_iri:
                return _k
    return None
