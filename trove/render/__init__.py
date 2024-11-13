from django import http

from trove import exceptions as trove_exceptions
from ._base import BaseRenderer
from .jsonapi import RdfJsonapiRenderer
from .html_browse import RdfHtmlBrowseRenderer
from .turtle import RdfTurtleRenderer
from .jsonld import RdfJsonldRenderer
from .simple_csv import TrovesearchCsvRenderer
from .simple_json import TrovesearchSimpleJsonRenderer
from .simple_tsv import TrovesearchTsvRenderer


__all__ = ('get_renderer_type',)

RENDERERS: tuple[type[BaseRenderer], ...] = (
    RdfHtmlBrowseRenderer,
    RdfJsonapiRenderer,
    RdfTurtleRenderer,
    RdfJsonldRenderer,
    TrovesearchCsvRenderer,
    TrovesearchSimpleJsonRenderer,
    TrovesearchTsvRenderer,
)

RENDERER_BY_MEDIATYPE = {
    _renderer_type.MEDIATYPE: _renderer_type
    for _renderer_type in RENDERERS
}
DEFAULT_RENDERER = RdfJsonapiRenderer  # the most stable one


def get_renderer_type(request: http.HttpRequest) -> type[BaseRenderer]:
    # TODO: recognize .extension?
    _chosen_renderer_type = None
    _requested_mediatype = request.GET.get('acceptMediatype')
    if _requested_mediatype:
        try:
            _chosen_renderer_type = RENDERER_BY_MEDIATYPE[_requested_mediatype]
        except KeyError:
            raise trove_exceptions.CannotRenderMediatype(_requested_mediatype)
    else:
        for _mediatype, _renderer_type in RENDERER_BY_MEDIATYPE.items():
            if request.accepts(_mediatype):
                _chosen_renderer_type = _renderer_type
                break
    if _chosen_renderer_type is None:
        _chosen_renderer_type = DEFAULT_RENDERER
    return _chosen_renderer_type
