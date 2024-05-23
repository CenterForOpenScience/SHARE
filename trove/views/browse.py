from django.shortcuts import redirect
from django.views import View
from primitive_metadata import primitive_rdf

from trove import models as trove_db
from trove.render import get_renderer
from trove.util.iris import unquote_iri, get_sufficiently_unique_iri
from trove.vocab import namespaces as ns


class BrowseIriView(View):
    def get(self, request, **kwargs):
        _iri_param = kwargs.get('iri') or request.GET.get('iri')
        if not _iri_param:
            raise ValueError('TODO: random browse?')
        _iri = unquote_iri(_iri_param)
        _trove_term = _recognize_trove_term(_iri)
        if _trove_term is not None:
            return redirect('trove-vocab', vocab_term=_trove_term)
        _focus_iri, _tripledict = _get_latest_cardf(_iri)
        return get_renderer(request).render_response(
            _tripledict,
            _focus_iri,
            headers={
                'Content-Disposition': 'inline',
            },
        )


def _get_latest_cardf(iri: str):
    try:
        _identifier = trove_db.ResourceIdentifier.objects.get_for_iri(iri)
    except trove_db.ResourceIdentifier.DoesNotExist:
        return iri, {}
    else:
        _rdf_qs = (
            trove_db.LatestIndexcardRdf.objects
            .filter(indexcard__focus_identifier_set=_identifier)
            .select_related('indexcard')
        )
        _focus_iri = None
        _combined_rdf = primitive_rdf.RdfGraph({})
        for _indexcard_rdf in _rdf_qs:
            if _focus_iri is None:
                _focus_iri = _indexcard_rdf.focus_iri
            _combined_rdf.add((_focus_iri, ns.FOAF.primaryTopicOf, _indexcard_rdf.indexcard.get_iri()))
            for _triple in primitive_rdf.iter_tripleset(_indexcard_rdf.as_rdf_tripledict()):
                _combined_rdf.add(_triple)
        return _focus_iri, _combined_rdf.tripledict


def _recognize_trove_term(iri: str):
    _suffuniq_iri = get_sufficiently_unique_iri(iri)
    _suffuniq_trove = get_sufficiently_unique_iri(str(ns.TROVE))
    if _suffuniq_iri.startswith(_suffuniq_trove):
        return primitive_rdf.iri_minus_namespace(_suffuniq_iri, _suffuniq_trove).strip('/')
    return None
