from django import http
from django.views import View

from trove import exceptions as trove_exceptions
from trove.render import (
    DEFAULT_RENDERER_TYPE,
    get_renderer_type,
)
from trove.vocab.namespaces import TROVE
from trove.vocab.trove import TROVE_API_THESAURUS
from ._responder import (
    make_http_error_response,
    make_http_response,
)


class TroveVocabView(View):
    def get(self, request, vocab_term):
        _iri = TROVE[vocab_term]
        try:
            _data = {_iri: TROVE_API_THESAURUS[_iri]}
        except KeyError:
            raise http.Http404
        try:
            _renderer_type = get_renderer_type(request)
            _renderer = _renderer_type(_iri, _data)
            return make_http_response(
                content_rendering=_renderer.render_document(),
                http_request=request,
            )
        except trove_exceptions.CannotRenderMediatype as _error:
            return make_http_error_response(
                error=_error,
                renderer_type=DEFAULT_RENDERER_TYPE,
            )
        except trove_exceptions.TroveError as _error:
            return make_http_error_response(
                error=_error,
                renderer_type=_renderer_type,
            )
