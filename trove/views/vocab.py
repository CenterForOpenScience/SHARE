from urllib.parse import urlencode

from django import http
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View

from trove.vocab.namespaces import TROVE
from trove.vocab.trove import TROVE_API_THESAURUS


class TroveVocabView(View):
    def get(self, request, vocab_term):
        _iri = TROVE[vocab_term]
        if _iri not in TROVE_API_THESAURUS:
            raise http.Http404
        _browse_url = '?'.join((
            reverse('trove-browse'),
            urlencode({'iri': _iri}),
        ))
        return redirect(_browse_url)
