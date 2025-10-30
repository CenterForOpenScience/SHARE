from django import http

from trove import exceptions as trove_exceptions
from trove.vocab.mediatypes import strip_mediatype_parameters
from ._base import BaseRenderer
from .jsonapi import RdfJsonapiRenderer
from .html_browse import RdfHtmlBrowseRenderer
from .turtle import RdfTurtleRenderer
from .jsonld import RdfJsonldRenderer
from .cardsearch_rss import CardsearchRssRenderer
from .cardsearch_atom import CardsearchAtomRenderer
from .trovesearch_csv import TrovesearchCsvRenderer
from .trovesearch_json import TrovesearchJsonRenderer
from .trovesearch_tsv import TrovesearchTsvRenderer


__all__ = ('get_renderer_type', 'BaseRenderer')

RENDERERS: tuple[type[BaseRenderer], ...] = (
    RdfHtmlBrowseRenderer,
    RdfJsonapiRenderer,
    RdfTurtleRenderer,
    RdfJsonldRenderer,
    TrovesearchCsvRenderer,
    TrovesearchJsonRenderer,
    TrovesearchTsvRenderer,
)
CARDSEARCH_ONLY_RENDERERS = (  # TODO: use/consider
    CardsearchRssRenderer,
    CardsearchAtomRenderer,
)

RENDERER_BY_MEDIATYPE = {
    _renderer_type.MEDIATYPE: _renderer_type
    for _renderer_type in RENDERERS
}
DEFAULT_RENDERER_TYPE = RdfJsonapiRenderer  # the most stable one?


def get_renderer_type(request: http.HttpRequest) -> type[BaseRenderer]:
    # TODO: recognize .extension?
    _chosen_renderer_type = None
    _requested_mediatype = request.GET.get('acceptMediatype')
    if _requested_mediatype:
        try:
            _chosen_renderer_type = RENDERER_BY_MEDIATYPE[
                strip_mediatype_parameters(_requested_mediatype)
            ]
        except KeyError:
            raise trove_exceptions.CannotRenderMediatype(_requested_mediatype)
    else:
        for _mediatype, _renderer_type in RENDERER_BY_MEDIATYPE.items():
            if request.accepts(_mediatype):
                _chosen_renderer_type = _renderer_type
                break
    if _chosen_renderer_type is None:
        _chosen_renderer_type = DEFAULT_RENDERER_TYPE
    return _chosen_renderer_type
