from typing import Iterable

from django import http
from django.shortcuts import redirect
from django.views import View
from primitive_metadata import primitive_rdf

from trove import models as trove_db
from trove.render import get_renderer
from trove.util.iris import unquote_iri, get_sufficiently_unique_iri
from trove.vocab.namespaces import TROVE


class BrowseIriView(View):
    def get(self, request, iri):
        _iri = unquote_iri(iri)
        _trove_term = _recognize_trove_term(_iri)
        if _trove_term is not None:
            return redirect('trove-vocab', vocab_term=_trove_term)
        try:
            _identifier = trove_db.ResourceIdentifier.objects.get_for_iri(_iri)
        except trove_db.ResourceIdentifier.DoesNotExist:
            raise http.Http404
        _rdf_qs = (
            trove_db.LatestIndexcardRdf.objects
            .filter(indexcard__focus_identifier_set=_identifier)
        )
        # TODO: query param for split/combined
        _tripledict = _merge_tripledicts(
            _indexcard_rdf.as_rdf_tripledict()
            for _indexcard_rdf in _rdf_qs
        )
        return get_renderer(request).render_response(_tripledict, _iri)


def _merge_tripledicts(tripledicts: Iterable[dict]):
    _merged = primitive_rdf.RdfGraph({})
    for _tripledict in tripledicts:
        for _triple in primitive_rdf.iter_tripleset(_tripledict):
            _merged.add(_triple)
    return _merged.tripledict


def _recognize_trove_term(iri: str):
    _suffuniq_iri = get_sufficiently_unique_iri(iri)
    _suffuniq_trove = get_sufficiently_unique_iri(str(TROVE))
    if _suffuniq_iri.startswith(_suffuniq_trove):
        return primitive_rdf.iri_minus_namespace(_suffuniq_iri, _suffuniq_trove).strip('/')
    return None
