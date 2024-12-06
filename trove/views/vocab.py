from django import http
from django.views import View

from trove.render import get_renderer_type
from trove.vocab.namespaces import TROVE
from trove.vocab.trove import TROVE_API_THESAURUS
from ._responder import make_http_response


class TroveVocabView(View):
    def get(self, request, vocab_term):
        _iri = TROVE[vocab_term]
        try:
            _data = {_iri: TROVE_API_THESAURUS[_iri]}
        except KeyError:
            raise http.Http404
        _renderer = get_renderer_type(request)(_iri, _data)
        return make_http_response(
            content_rendering=_renderer.render_document(),
            http_request=request,
        )
