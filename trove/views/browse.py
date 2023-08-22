import datetime
import random

from django import http
from django.views.generic.base import TemplateView
from gather import primitive_rdf

from trove import models as trove_db
from trove.util.iri_labeler import IriLabeler
from trove.vocab.osfmap import osfmap_labeler


class BrowseIriView(TemplateView):
    template_name = 'browse/browse_piri.html'

    def get_context_data(self, **kwargs):
        _context = super().get_context_data(**kwargs)
        try:
            # TODO: iri query param (stop with the `///`)
            # TODO: support some prefixes for convenience
            _identifier = trove_db.ResourceIdentifier.objects.get_for_iri(kwargs['iri'])
        except trove_db.ResourceIdentifier.DoesNotExist:
            raise http.Http404
        _context['rdf_indexcard_list'] = [
            _IndexcardContextBuilder(_indexcard_rdf, labeler=osfmap_labeler).build(_identifier)
            for _indexcard_rdf in self._get_indexcard_rdf_set(_identifier)
        ]
        _context['random_ratio'] = random.random()
        return _context

    def _get_indexcard_rdf_set(self, identifier: trove_db.ResourceIdentifier):
        return trove_db.LatestIndexcardRdf.objects.filter(indexcard__focus_identifier_set=identifier)


class _IndexcardContextBuilder:
    def __init__(self, indexcard_rdf: trove_db.IndexcardRdf, labeler: IriLabeler):
        self._labeler = labeler
        self._tripledict = indexcard_rdf.as_rdf_tripledict()
        self._visiting = set()

    def build(self, identifier: trove_db.ResourceIdentifier) -> dict:
        _iri = identifier.find_equivalent_iri(self._tripledict)
        self._visiting.add(_iri)
        _indexcard_context = {
            'focus': self._iri_context(_iri),
            'nested_twopleset': self._nested_twopleset_context(self._tripledict[_iri]),
        }
        self._visiting.remove(_iri)
        return _indexcard_context

    def _nested_twopleset_context(self, twopledict: primitive_rdf.RdfTwopleDictionary) -> list:
        _nested_twopleset = []
        for _predicate_iri, _objectset in twopledict.items():
            _nested_twopleset.append({
                'predicate': self._iri_context(_predicate_iri),
                'objectset': [
                    self._nested_object_context(_obj)
                    for _obj in _objectset
                ],
            })
        return _nested_twopleset

    def _nested_object_context(self, rdfobject: primitive_rdf.RdfObject) -> dict:
        if isinstance(rdfobject, str):
            _iriref_context = self._iri_context(rdfobject)
            if (rdfobject not in self._visiting) and (rdfobject in self._tripledict):
                self._visiting.add(rdfobject)
                _iriref_context['nested_twopleset'] = self._nested_twopleset_context(
                    self._tripledict[rdfobject],
                )
                self._visiting.remove(rdfobject)
            return _iriref_context
        if isinstance(rdfobject, primitive_rdf.Text):
            return {
                'literal': {
                    'value': rdfobject.unicode_text,
                    # TODO: language/datatype
                },
            }
        if isinstance(rdfobject, (int, float, datetime.date)):
            return {
                'literal': {
                    'value': str(rdfobject),
                    # TODO: language/datatype
                },
            }
        if isinstance(rdfobject, frozenset):
            return {
                'nested_twopleset': self._nested_twopleset_context(
                    primitive_rdf.twopleset_as_twopledict(rdfobject),
                ),
            }
        raise ValueError(f'unrecognized rdf object: {rdfobject}')

    def _iri_context(self, iri: str) -> dict:
        return {
            'iri': iri,
            'label': self._labeler.get_label_or_iri(iri),
        }
