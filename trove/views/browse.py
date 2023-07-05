import datetime
import random

from django import http
from django.views.generic.base import TemplateView
import gather

from share.util import rdfutil
from trove import models as trove_db
from trove.vocab.osfmap import osfmap_labeler


class BrowseIriView(TemplateView):
    template_name = 'browse/browse_piri.html'

    def get_context_data(self, **kwargs):
        _context = super().get_context_data(**kwargs)
        try:
            # TODO: support some prefixes for convenience
            _piri = trove_db.PersistentIri.objects.get_for_iri(kwargs['iri'])
        except trove_db.PersistentIri.DoesNotExist:
            raise http.Http404
        _context['rdf_indexcard_list'] = [
            _IndexcardContextBuilder(_indexcard, labeler=osfmap_labeler).build(_piri)
            for _indexcard in self._get_indexcards(_piri)
        ]
        _context['random_ratio'] = random.random()
        return _context

    def _get_indexcards(self, piri: trove_db.PersistentIri):
        return trove_db.RdfIndexcard.objects.filter(focus_piri_set=piri)


class _IndexcardContextBuilder:
    def __init__(self, indexcard: trove_db.RdfIndexcard, labeler: rdfutil.IriLabeler):
        self._labeler = labeler
        self._tripledict = indexcard.as_rdf_tripledict()
        self._visiting = set()

    def build(self, piri: trove_db.PersistentIri) -> dict:
        _iri = piri.find_equivalent_iri(self._tripledict)
        self._visiting.add(_iri)
        _indexcard_context = {
            'focus': self._iri_context(_iri),
            'nested_twopleset': self._nested_twopleset_context(self._tripledict[_iri]),
        }
        self._visiting.remove(_iri)
        return _indexcard_context

    def _nested_twopleset_context(self, twopledict: gather.RdfTwopleDictionary) -> list:
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

    def _nested_object_context(self, rdfobject: gather.RdfObject) -> dict:
        if isinstance(rdfobject, str):
            _iriref_context = self._iri_context(rdfobject)
            if (rdfobject not in self._visiting) and (rdfobject in self._tripledict):
                self._visiting.add(rdfobject)
                _iriref_context['nested_twopleset'] = self._nested_twopleset_context(
                    self._tripledict[rdfobject],
                )
                self._visiting.remove(rdfobject)
            return _iriref_context
        if isinstance(rdfobject, gather.Text):
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
                    gather.twopleset_as_twopledict(rdfobject),
                ),
            }
        raise ValueError(f'unrecognized rdf object: {rdfobject}')

    def _iri_context(self, iri: str) -> dict:
        return {
            'iri': iri,
            'label': self._labeler.get_label_or_iri(iri),
        }
