import contextlib
import datetime
import random
from typing import Optional
from urllib.parse import quote
from xml.etree import ElementTree

from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from primitive_metadata import primitive_rdf

from trove.vocab.namespaces import TROVE, RDF


class RdfHtmlBrowseRenderer:
    MEDIATYPE = 'text/html'

    def __init__(
        self, data: primitive_rdf.RdfTripleDictionary, *,
        iri_shorthand: Optional[primitive_rdf.IriShorthand] = None,
    ):
        self.data = data
        self.iri_shorthand = iri_shorthand or primitive_rdf.IriShorthand({
            'trove': TROVE,
        })

    def render_document(self, focus_iri: str) -> str:
        # TODO: <!DOCTYPE html>
        self.__html_builder = ElementTree.TreeBuilder()
        with self.__nest('html'):
            with self.__nest('head'):
                self.__leaf('link', attrs={
                    'rel': 'stylesheet',
                    'href': staticfiles_storage.url('css/browse.css'),
                })
            _body_attrs = {
                'class': 'BrowseWrapper',
                'style': f'--random-turn: {random.random()}turn;',
            }
            with self.__nest('body', attrs=_body_attrs):
                self._render_tripledict(self.data, focus_iri),
        _html_etree = self.__html_builder.close()
        del self.__html_builder
        return ElementTree.tostring(_html_etree, encoding='unicode', method='html')

    def _render_tripledict(self, tripledict: primitive_rdf.RdfTripleDictionary, focus_iri: str):
        with self.__nest('article', attrs={'class': 'Browse'}):
            for _subj, _twopledict in tripledict.items():
                with self.__nest('section'):
                    self.__leaf('h2', text=_subj, attrs={
                        'id': quote(self.iri_shorthand.compact_iri(_subj)),
                    })
                    self.__twopleset(_twopledict)

    @contextlib.contextmanager
    def __nest(self, tag_name, attrs=None, visible=False):
        _attrs = {**attrs} if attrs else {}
        if visible:
            _attrs['class'] = (
                ' '.join((_attrs['class'], 'VisibleNest'))
                if 'class' in _attrs
                else 'VisibleNest'
            )
        self.__html_builder.start(tag_name, _attrs)
        yield
        self.__html_builder.end(tag_name)

    def __leaf(self, tag_name, *, text=None, attrs=None):
        self.__html_builder.start(tag_name, attrs or {})
        if text is not None:
            self.__html_builder.data(text)
        self.__html_builder.end(tag_name)

    def __twopleset(self, twoples: primitive_rdf.RdfTwopleDictionary):
        with self.__nest('ul', {'class': 'Browse__nested_twopleset'}):
            for _pred, _obj_set in twoples.items():
                with self.__nest('li', {'class': 'Browse__nested_twople'}, visible=True):
                    self.__link(_pred)
                    with self.__nest('ul', {'class': 'Browse__objectset'}):
                        for _obj in _obj_set:
                            with self.__nest('li', {'class': 'Browse__object'}, visible=True):
                                self.__obj(_obj)

    def __obj(self, obj: primitive_rdf.RdfObject):
        if isinstance(obj, frozenset):
            if (RDF.type, RDF.Seq) in obj:
                with self.__nest('ol'):
                    for _seq_obj in primitive_rdf.sequence_objects_in_order(obj):
                        with self.__nest('li', visible=True):
                            self.__obj(_seq_obj)
            else:
                self.__twopleset(primitive_rdf.twopledict_from_twopleset(obj))
        elif isinstance(obj, primitive_rdf.Datum):
            # TODO language tag
            self.__leaf('q', text=obj.unicode_value)
        elif isinstance(obj, str):
            # TODO link to anchor on this page?
            self.__link(obj)
        elif isinstance(obj, (float, int, datetime.date)):
            # TODO datatype?
            self.__leaf('q', text=str(obj))

    def __link(self, iri: str):
        self.__leaf('a', text=self.iri_shorthand.compact_iri(iri), attrs={
            'href': self.__href_for_iri(iri),
        })

    def __href_for_iri(self, iri: str):
        if iri in self.data:
            return f'#{quote(self.iri_shorthand.compact_iri(iri))}'
        if iri in TROVE:
            return reverse('trove-vocab', kwargs={
                'vocab_term': primitive_rdf.iri_minus_namespace(iri, namespace=TROVE),
            })
        return reverse('trovetrove:browse-iri', kwargs={
            'iri': iri,
        })
