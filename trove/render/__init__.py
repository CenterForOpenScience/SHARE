from django import http

from trove import exceptions as trove_exceptions
from trove.vocab.trove import TROVE_API_THESAURUS
from trove.vocab.namespaces import NAMESPACES_SHORTHAND
from ._base import BaseRenderer
from .jsonapi import RdfJsonapiRenderer
from .html_browse import RdfHtmlBrowseRenderer
from .turtle import RdfTurtleRenderer
from .jsonld import RdfJsonldRenderer
from .simple_json import TrovesearchSimpleJsonRenderer


__all__ = ('get_renderer',)

RENDERERS: tuple[type[BaseRenderer], ...] = (
    RdfHtmlBrowseRenderer,
    RdfJsonapiRenderer,
    RdfTurtleRenderer,
    RdfJsonldRenderer,
    TrovesearchSimpleJsonRenderer,
)

RENDERER_BY_MEDIATYPE = {
    _renderer_cls.MEDIATYPE: _renderer_cls
    for _renderer_cls in RENDERERS
}
DEFAULT_RENDERER = RdfJsonapiRenderer  # the most stable one


def get_renderer(request: http.HttpRequest):
    # TODO: recognize .extension?
    _chosen_renderer_cls = None
    _requested_mediatype = request.GET.get('acceptMediatype')
    if _requested_mediatype:
        try:
            _chosen_renderer_cls = RENDERER_BY_MEDIATYPE[_requested_mediatype]
        except KeyError:
            raise trove_exceptions.CannotRenderMediatype(_requested_mediatype)
    else:
        for _mediatype, _renderer_cls in RENDERER_BY_MEDIATYPE.items():
            if request.accepts(_mediatype):
                _chosen_renderer_cls = _renderer_cls
                break
    if _chosen_renderer_cls is None:
        _chosen_renderer_cls = DEFAULT_RENDERER
    return _chosen_renderer_cls(
        iri_shorthand=NAMESPACES_SHORTHAND,
        thesaurus=TROVE_API_THESAURUS,
        request=request,
    )
