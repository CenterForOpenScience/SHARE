from __future__ import annotations
import abc
from collections.abc import Container
import functools
from typing import (
    ClassVar,
    TYPE_CHECKING,
)

from django.views import View
from primitive_metadata import gather
from primitive_metadata import primitive_rdf as rdf

from trove import exceptions as trove_exceptions
from trove.util.trove_params import BasicTroveParams
from trove.vocab.namespaces import TROVE, RDF
from trove.render import (
    DEFAULT_RENDERER_TYPE,
    get_renderer_type,
)
from ._gather_ask import ask_gathering_from_params
from ._responder import (
    make_http_error_response,
    make_http_response,
)
if TYPE_CHECKING:
    from django.http import HttpResponse, StreamingHttpResponse, HttpRequest
    from trove.render import BaseRenderer
    from trove.render._rendering import ProtoRendering


__all__ = (
    'GatheredTroveView',
    'StaticTroveView',
)


class BaseTroveView(View, abc.ABC):
    # optional ClassVars:
    params_type: ClassVar[type[BasicTroveParams]] = BasicTroveParams

    @abc.abstractmethod
    def _render_response_content(self, request, params, renderer_type: type[BaseRenderer], url_kwargs) -> ProtoRendering:
        raise NotImplementedError

    def get(self, request: HttpRequest, **kwargs: str) -> HttpResponse | StreamingHttpResponse:
        try:
            _renderer_type = get_renderer_type(request)
        except trove_exceptions.CannotRenderMediatype as _error:
            return make_http_error_response(
                error=_error,
                renderer_type=DEFAULT_RENDERER_TYPE,
            )
        try:
            _params = self._parse_params(request)
            return make_http_response(
                content_rendering=self._render_response_content(request, _params, _renderer_type, kwargs),
                http_request=request,
            )
        except trove_exceptions.TroveError as _error:
            return make_http_error_response(
                error=_error,
                renderer_type=_renderer_type,
            )

    def _parse_params(self, request: HttpRequest):
        return self.params_type.from_querystring(request.META['QUERY_STRING'])


class GatheredTroveView(BaseTroveView, abc.ABC):
    # ClassVars expected on inheritors:
    gathering_organizer: ClassVar[gather.GatheringOrganizer]
    # optional ClassVars:
    focus_type_iris: ClassVar[Container[str]] = ()

    def _render_response_content(self, request, params, renderer_type: type[BaseRenderer], url_kwargs):
        _focus = self._build_focus(request, params, url_kwargs)
        _renderer = self._gather_to_renderer(_focus, params, renderer_type)
        return _renderer.render_document()

    def _gather_to_renderer(self, focus, params, renderer_type: type[BaseRenderer]) -> BaseRenderer:
        _gathering = self._build_gathering(params, renderer_type)
        if renderer_type.PASSIVE_RENDER:
            ask_gathering_from_params(_gathering, params, focus)
        return renderer_type(focus, _gathering)

    def _get_focus_iri(self, request, params) -> str:
        return request.build_absolute_uri()

    def _build_focus(self, request, params, url_kwargs) -> gather.Focus:
        return gather.Focus.new(self._get_focus_iri(request, params), self.focus_type_iris)

    def _build_gathering(self, params, renderer_type: type[BaseRenderer]) -> gather.Gathering:
        return self.gathering_organizer.new_gathering(
            self._get_gatherer_kwargs(params, renderer_type),
        )

    def _get_gatherer_kwargs(self, params, renderer_type) -> dict:
        _kwargs = {}
        _deriver_kw = _get_param_keyword(TROVE.deriverIRI, self.gathering_organizer)
        if _deriver_kw:
            _kwargs[_deriver_kw] = renderer_type.get_deriver_iri(params.blend_cards)
        _blend_kw = _get_param_keyword(TROVE.blendCards, self.gathering_organizer)
        if _blend_kw:
            _kwargs[_blend_kw] = params.blend_cards
        return _kwargs


class StaticTroveView(BaseTroveView, abc.ABC):
    @classmethod
    @abc.abstractmethod
    def get_focus_iri(cls) -> str:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_static_triples(cls, focus_iri: str) -> rdf.RdfTripleDictionary:
        raise NotImplementedError

    @classmethod
    @functools.cache
    def cached_static_triples(cls, focus_iri):
        return cls.get_static_triples(focus_iri)

    def _render_response_content(self, request, params, renderer_type: type[BaseRenderer], url_kwargs):
        _focus_iri = self.get_focus_iri()
        _triples = self.cached_static_triples(_focus_iri)
        _focus = gather.Focus.new(
            _focus_iri,
            type_iris=_triples.get(_focus_iri, {}).get(RDF.type, ()),
        )

        class _FakeStaticGathering:
            gatherer_kwargs: dict = {}

            def leaf_a_record(self):
                return _triples

        _renderer = renderer_type(
            response_focus=_focus,
            response_gathering=_FakeStaticGathering(),
        )
        return _renderer.render_document()


###
# local helpers

def _get_param_keyword(param_iri: str, organizer: gather.GatheringOrganizer) -> str | None:
    if param_iri in organizer.norms.param_iris:
        for (_k, _v) in organizer.gatherer_params.items():
            if _v == param_iri:
                return _k
    return None
