import contextlib
import datetime
import random
from typing import Optional, Iterable
from urllib.parse import quote, urlsplit
from xml.etree import ElementTree

from django.contrib.staticfiles.storage import staticfiles_storage
from django.http import HttpRequest
from django.urls import reverse
from primitive_metadata import primitive_rdf

from trove.vocab.namespaces import TROVE, RDF, STATIC_SHORTHAND


class RdfHtmlBrowseRenderer:
    MEDIATYPE = 'text/html; charset=utf-8'

    def __init__(
        self, data: primitive_rdf.RdfTripleDictionary, *,
        iri_shorthand: Optional[primitive_rdf.IriShorthand] = None,
        request: Optional[HttpRequest] = None,
    ):
        self.data = data
        self.request = request
        self.iri_shorthand = iri_shorthand or STATIC_SHORTHAND
        self.rendered_etree = None
        self.__html_builder = None
        self.__visiting_iris = None
        self.__heading_depth = None

    def render_document(self, focus_iri: str) -> str:
        # TODO: <!DOCTYPE html>
        with self.__rendering():
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
                    self.__triples(focus_iri),
        return ''.join((
            '<!DOCTYPE html>',
            ElementTree.tostring(self.rendered_etree, encoding='unicode', method='html'),
        ))

    ###
    # private rdf-rendering helpers

    def __triples(self, focus_iri: str):
        with self.__visiting(focus_iri):
            with self.__h_tag() as _h_tag:
                with self.__nest('section', attrs={'class': 'Browse__card'}, visible=True):
                    with self.__nest('header'):
                        _label = self.__label_for_iri(focus_iri)
                        with self.__nest(_h_tag, attrs={'class': 'Browse__heading'}):
                            with self.__nest_link(focus_iri):
                                self.__leaf('dfn', text=_label, attrs={'id': quote(focus_iri)})
                        _compact_focus = self.iri_shorthand.compact_iri(focus_iri)
                        if _compact_focus != _label:
                            self.__leaf('code', text=_compact_focus)
                        if _compact_focus != focus_iri:
                            self.__leaf('code', text=focus_iri)
                    self.__twoples(self.data.get(focus_iri, {}))
        # TODO: <details> with disconnected triples (unreachable from given focus)

    def __twoples(self, twopledict: primitive_rdf.RdfTwopleDictionary):
        with self.__nest('ul', {'class': 'Browse__nested_twopleset'}):
            for _pred, _obj_set in _shuffled(twopledict.items()):
                with self.__nest('li', {'class': 'Browse__nested_twople'}, visible=True):
                    self.__leaf_link(_pred)
                    # TODO: use a vocab, not static property iris
                    if _pred == TROVE.resourceMetadata:
                        _focus_iris = twopledict[TROVE.resourceIdentifier]  # assumed
                        _focus_iri = None
                        _quoted_triples = set()
                        for _obj in _shuffled(_obj_set):
                            if isinstance(_obj, primitive_rdf.QuotedTriple):
                                _quoted_triples.add(_obj)
                                (_subj, _, _) = _obj
                                if _subj in _focus_iris:
                                    _focus_iri = _subj
                        assert _focus_iri is not None
                        self.__quoted_graph(_focus_iri, _quoted_triples)
                    else:
                        with self.__nest('ul', {'class': 'Browse__objectset'}):
                            for _obj in _shuffled(_obj_set):
                                with self.__nest('li', {'class': 'Browse__object'}, visible=True):
                                    self.__obj(_obj)

    def __obj(self, obj: primitive_rdf.RdfObject):
        if isinstance(obj, str):  # iri
            # TODO: detect whether indexcard?
            if obj in self.data:
                if obj in self.__visiting_iris:
                    self.__leaf_link(obj)  # TODO: consider
                else:
                    self.__triples(obj)
            else:
                self.__leaf_link(obj)
        elif isinstance(obj, frozenset):  # blanknode
            if (RDF.type, RDF.Seq) in obj:
                self.__sequence(obj)
            else:
                self.__twoples(primitive_rdf.twopledict_from_twopleset(obj))
        elif isinstance(obj, primitive_rdf.Literal):
            # TODO language tag
            self.__leaf('q', text=obj.unicode_value)
        elif isinstance(obj, (float, int, datetime.date)):
            # TODO datatype?
            self.__leaf('q', text=str(obj))

    def __sequence(self, sequence_twoples: frozenset):
        _obj_in_order = list(primitive_rdf.sequence_objects_in_order(sequence_twoples))
        with self.__nest('details', attrs={'open': ''}):
            self.__leaf('summary', text=str(len(_obj_in_order)))
            with self.__nest('ol'):  # TODO: style?
                for _seq_obj in _obj_in_order:
                    with self.__nest('li', visible=True):
                        self.__obj(_seq_obj)

    def __quoted_graph(self, focus_iri, quoted_triples):
        _quoted_graph = primitive_rdf.RdfGraph({})
        for _triple in quoted_triples:
            _quoted_graph.add(_triple)
        with self.__quoted_data(_quoted_graph.tripledict):
            self.__triples(focus_iri)

    ###
    # private html-building helpers

    @contextlib.contextmanager
    def __rendering(self):
        self.__html_builder = ElementTree.TreeBuilder()
        self.__visiting_iris = set()
        try:
            yield
            self.rendered_etree = self.__html_builder.close()
        finally:
            self.__html_builder = None
            self.__visiting_iris = None

    @contextlib.contextmanager
    def __visiting(self, iri: str):
        assert iri not in self.__visiting_iris
        self.__visiting_iris.add(iri)
        try:
            yield
        finally:
            self.__visiting_iris.remove(iri)

    @contextlib.contextmanager
    def __h_tag(self):
        _outer_heading_depth = self.__heading_depth
        if not _outer_heading_depth:
            self.__heading_depth = 1
        elif _outer_heading_depth < 6:  # h6 deepest
            self.__heading_depth += 1
        try:
            yield f'h{self.__heading_depth}'
        finally:
            self.__heading_depth = _outer_heading_depth

    @contextlib.contextmanager
    def __quoted_data(self, quoted_data: dict):
        _outer_data = self.data
        _outer_visiting_iris = self.__visiting_iris
        self.data = quoted_data
        self.__visiting_iris = set()
        try:
            yield
        finally:
            self.data = _outer_data
            self.__visiting_iris = _outer_visiting_iris

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

    def __nest_link(self, iri: str):
        return self.__nest('a', attrs={'href': self.__href_for_iri(iri)})

    def __leaf_link(self, iri: str):
        with self.__nest_link(iri):
            self.__html_builder.data(self.iri_shorthand.compact_iri(iri))

    def __href_for_iri(self, iri: str):
        if self.request and (self.request.get_host() == urlsplit(iri).netloc):
            return iri
        if iri in TROVE:
            return reverse('trove-vocab', kwargs={
                'vocab_term': primitive_rdf.iri_minus_namespace(iri, namespace=TROVE),
            })
        return reverse('trovetrove:browse-iri', kwargs={'iri': iri})

    def __label_for_iri(self, iri: str):
        # TODO: get actual label in requested language
        return self.iri_shorthand.compact_iri(iri)


def _shuffled(items: Iterable):
    _item_list = list(items)
    random.shuffle(_item_list)
    return _item_list
