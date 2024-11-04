from django import http
from django.views import View

from trove.render import get_renderer_class
from trove.vocab.namespaces import TROVE
from trove.vocab.trove import TROVE_API_THESAURUS


class TroveVocabView(View):
    def get(self, request, vocab_term):
        _iri = TROVE[vocab_term]
        try:
            _data = {_iri: TROVE_API_THESAURUS[_iri]}
        except KeyError:
            raise http.Http404
        return get_renderer_class(request)(_iri, _data).render_response()
