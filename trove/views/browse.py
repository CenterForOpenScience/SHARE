from django import http
from django.shortcuts import redirect
from django.views import View
from primitive_metadata import primitive_rdf

from trove import models as trove_db
from trove.render import get_renderer_type
from trove.util.iris import unquote_iri, get_sufficiently_unique_iri
from trove.vocab import namespaces as ns
from trove.vocab import static_vocab
from ._responder import make_http_response


class BrowseIriView(View):
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


def _get_latest_cardf(iri: str):
    _combined_rdf = primitive_rdf.RdfGraph({})
    try:
        _identifier = trove_db.ResourceIdentifier.objects.get_for_iri(iri)
    except trove_db.ResourceIdentifier.DoesNotExist:
        return iri, _combined_rdf
    else:
        _rdf_qs = (
            trove_db.LatestIndexcardRdf.objects
            .filter(indexcard__focus_identifier_set=_identifier)
            .select_related('indexcard')
        )
        _focus_iri = None
        for _indexcard_rdf in _rdf_qs:
            if _focus_iri is None:
                _focus_iri = _indexcard_rdf.focus_iri
            _combined_rdf.add((_focus_iri, ns.FOAF.primaryTopicOf, _indexcard_rdf.indexcard.get_iri()))
            for (_subj, _pred, _obj) in primitive_rdf.iter_tripleset(_indexcard_rdf.as_rdf_tripledict()):
                _combined_rdf.add(
                    (_focus_iri, _pred, _obj)
                    if _subj == _indexcard_rdf.focus_iri
                    else (_subj, _pred, _obj)
                )
        return (_focus_iri or iri), _combined_rdf


def _recognize_trove_term(suffuniq_iri: str):
    _suffuniq_trove = get_sufficiently_unique_iri(str(ns.TROVE))
    if suffuniq_iri.startswith(_suffuniq_trove):
        return primitive_rdf.iri_minus_namespace(suffuniq_iri, _suffuniq_trove).strip('/')
    return None
