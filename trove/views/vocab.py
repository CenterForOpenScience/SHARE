from __future__ import annotations
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View

from trove.vocab.namespaces import TROVE
from trove.vocab.trove import TROVE_API_THESAURUS
if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse, StreamingHttpResponse


class TroveVocabView(View):
    def get(self, request: HttpRequest, vocab_term: str) -> HttpResponse | StreamingHttpResponse:
        _iri = TROVE[vocab_term]
        if _iri not in TROVE_API_THESAURUS:
            raise Http404
        _browse_url = '?'.join((
            reverse('trove:browse-iri'),
            urlencode({'iri': _iri}),
        ))
        return redirect(_browse_url)
