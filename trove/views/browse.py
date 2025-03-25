import dataclasses

from django import http
from django.shortcuts import redirect
from django.views import View
from primitive_metadata import primitive_rdf

from trove import models as trove_db
from trove.render import get_renderer_type
from trove.util.iris import unquote_iri, get_sufficiently_unique_iri
from trove.vocab import namespaces as ns
from trove.trovebrowse_gathering import trovebrowse
from trove.trovesearch.search_params import BaseTroveParams
from ._base import BaseTroveView
from ._responder import make_http_response


@dataclasses.dataclass(frozen=True)
class BrowseParams(BaseTroveParams):
    iri: str


class BrowseIriView(BaseTroveView):
    organizer = trovebrowse
    params_type = BrowseParams

    def get(self, request, **kwargs):
        _iri_param = kwargs.get('iri') or request.GET.get('iri')
        if not _iri_param:
            raise http.Http404  # TODO: docs? random browse?
        _iri = ns.NAMESPACES_SHORTHAND.expand_iri(unquote_iri(_iri_param))
        _suffuniq_iri = get_sufficiently_unique_iri(_iri)
        _trove_term = _recognize_trove_term(_suffuniq_iri)
        if _trove_term is not None:
            return redirect('trove-vocab', vocab_term=_trove_term)
        _card_focus_iri, _combined_rdf = _get_latest_cardf(_iri)
        _thesaurus_entry = static_vocab.combined_thesaurus__suffuniq().get(_suffuniq_iri, {})
        if _thesaurus_entry:
            _combined_rdf.add_twopledict(_card_focus_iri, _thesaurus_entry)
        _renderer_type = get_renderer_type(request)
        _renderer = _renderer_type(
            _card_focus_iri,
            _combined_rdf.tripledict,
        )
        return make_http_response(
            content_rendering=_renderer.render_document(),
            http_headers=[('Content-Disposition', 'inline')],
            http_request=request,
        )


def _recognize_trove_term(suffuniq_iri: str):
    _suffuniq_trove = get_sufficiently_unique_iri(str(ns.TROVE))
    if suffuniq_iri.startswith(_suffuniq_trove):
        return primitive_rdf.iri_minus_namespace(suffuniq_iri, _suffuniq_trove).strip('/')
    return None
