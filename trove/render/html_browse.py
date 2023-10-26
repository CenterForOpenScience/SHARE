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

    rendered_etree = None

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
        with self.__rendering(focus_iri):
            with self.__nest('html'):  # TODO: lang (according to request -- also translate)
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
                    self.__render_tripledict(focus_iri),
        return ElementTree.tostring(self.rendered_etree, encoding='unicode', method='html')

    ###
    # private implementation

    @contextlib.contextmanager
    def __rendering(self, focus_iri: str):
        self.__html_builder = ElementTree.TreeBuilder()
        self.__visiting_iris = set([focus_iri])
        try:
            yield
            self.rendered_etree = self.__html_builder.close()
        finally:
            del self.__html_builder
            del self.__visiting_iris

    @contextlib.contextmanager
    def __visiting(self, iri: str):
        assert iri not in self.__visiting_iris
        self.__visiting_iris.add(iri)
        try:
            yield
        finally:
            self.__visiting_iris.remove(iri)

    def __render_tripledict(self, focus_iri: str):
        with self.__nest('article', attrs={'class': 'Browse'}):
            with self.__nest('header'):
                self.__leaf(
                    'h2',
                    text=self.iri_shorthand.compact_iri(focus_iri),
                    attrs={'id': quote(focus_iri)},
                )
            self.__twoples(self.data.get(focus_iri, {}))
        # TODO: <details> with disconnected triples (unreachable from given focus)

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

    def __twoples(self, twoples: primitive_rdf.RdfTwopleDictionary):
        with self.__nest('ul', {'class': 'Browse__nested_twopleset'}):
            for _pred, _obj_set in twoples.items():
                with self.__nest('li', {'class': 'Browse__nested_twople'}, visible=True):
                    self.__link(_pred)
                    with self.__nest('ul', {'class': 'Browse__objectset'}):
                        for _obj in _obj_set:
                            with self.__nest('li', {'class': 'Browse__object'}, visible=True):
                                self.__obj(_obj)

    def __obj(self, obj: primitive_rdf.RdfObject):
        if isinstance(obj, str):  # iri
            # TODO: detect whether indexcard?
            if obj in self.data:
                if obj in self.__visiting_iris:
                    self.__link(obj)  # TODO: consider
                else:
                    with self.__visiting(obj):
                        with self.__nest('details'):
                            self.__leaf('summary', text=self.iri_shorthand.compact_iri(obj))
                            self.__link(obj)  # TODO: consider
                            self.__twoples(self.data[obj])
            else:
                self.__link(obj)
        elif isinstance(obj, frozenset):  # blanknode
            if (RDF.type, RDF.Seq) in obj:
                _sequence = list(primitive_rdf.sequence_objects_in_order(obj))
                with self.__nest('details'):
                    self.__leaf('summary', text=str(len(_sequence)))
                    with self.__nest('ol', visible=True):  # TODO: style
                        for _seq_obj in _sequence:
                            with self.__nest('li', visible=True):
                                self.__obj(_seq_obj)
            else:
                self.__twoples(primitive_rdf.twopledict_from_twopleset(obj))
        elif isinstance(obj, primitive_rdf.Datum):
            # TODO language tag
            self.__leaf('q', text=obj.unicode_value)
        elif isinstance(obj, (float, int, datetime.date)):
            # TODO datatype?
            self.__leaf('q', text=str(obj))

    def __link(self, iri: str):
        self.__leaf(
            'a',
            text=self.iri_shorthand.compact_iri(iri),
            attrs={'href': self.__href_for_iri(iri)},
        )

    def __href_for_iri(self, iri: str):
        if iri in TROVE:
            return reverse('trove-vocab', kwargs={
                'vocab_term': primitive_rdf.iri_minus_namespace(iri, namespace=TROVE),
            })
        return reverse('trovetrove:browse-iri', kwargs={
            'iri': iri,
        })
