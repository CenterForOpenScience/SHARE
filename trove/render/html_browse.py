import contextlib
import dataclasses
import datetime
import markdown2
import random
from urllib.parse import quote, urlsplit, urlunsplit
from xml.etree.ElementTree import (
    Element,
    SubElement,
    tostring as etree_tostring,
    fromstring as etree_fromstring,
)

from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from primitive_metadata import primitive_rdf

from trove.util.iris import get_sufficiently_unique_iri
from trove.util.randomness import shuffled
from trove.vocab import mediatypes
from trove.vocab.namespaces import RDF
from trove.vocab.trove import trove_browse_link
from ._base import BaseRenderer

STABLE_MEDIATYPES = (mediatypes.JSONAPI,)
UNSTABLE_MEDIATYPES = (mediatypes.TURTLE, mediatypes.JSONLD, mediatypes.JSON,)


class RdfHtmlBrowseRenderer(BaseRenderer):
    MEDIATYPE = 'text/html; charset=utf-8'

    def render_document(self) -> str:
        _rendered_html_element = _HtmlRenderHelper(
            data=primitive_rdf.RdfGraph(self.response_data),
        ).render(self.response_focus_iri)
        return ''.join((
            '<!DOCTYPE html>',  # TODO: can etree put the doctype in?
            etree_tostring(_rendered_html_element, encoding='unicode', method='html'),
        ))


@dataclasses.dataclass
class _HtmlRenderHelper:
    data: primitive_rdf.RdfGraph
    rendered_element = None
    __current_element = None
    __visiting_iris = None
    __heading_depth = None

    def render(self, focus_iri: str) -> Element:
        with self.__rendering():
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
                self.__render_subj(focus_iri),
                self.__render_mediatype_links()
                # TODO: <details> with unvisited triples in self.data (unreachable from focus_iri)
        assert self.rendered_element
        return self.rendered_element

    def __render_mediatype_links(self):
        with self.__nest('nav', attrs={'class': 'VisibleNest Browse__card'}):
            self.__leaf('header', text='alternate mediatypes')
            with self.__nest('ul', attrs={'class': 'Browse__twopleset'}):
                for _mediatype in shuffled((*STABLE_MEDIATYPES, *UNSTABLE_MEDIATYPES)):
                    with self.__nest('li', attrs={'class': 'VisibleNest Browse__twople'}):
                        self.__mediatype_link(_mediatype)

    def __mediatype_link(self, mediatype: str):
        _qparams = self.http_request.GET.copy()
        _qparams['acceptMediatype'] = mediatype
        _href = urlunsplit((
            self.http_request.scheme,
            self.http_request.get_host(),
            self.http_request.path,
            _qparams.urlencode(),
            '',
        ))
        self.__leaf('a', text=mediatype, attrs={'href': _href})
        if mediatype in UNSTABLE_MEDIATYPES:
            self.__leaf('aside', text='(unstable)')
        if mediatype in STABLE_MEDIATYPES:
            with self.__nest('aside') as _aside:
                _aside.text = '(stable for '
                with self.__nest('a', attrs={'href': reverse('trovetrove:docs')}) as _link:
                    _link.text = 'documented use'
                    _link.tail = ')'

    def __render_subj(self, subj_iri: str, start_collapsed=False):
        _twopledict = self.data.tripledict.get(subj_iri, {})
        with self.__visiting(subj_iri):
            with self.__h_tag() as _h_tag:
                with self.__nest(
                    'details',
                    attrs={
                        'class': 'Browse__card',
                        **({} if start_collapsed else {'open': ''}),
                    },
                    visible=True,
                ):
                    with self.__nest('summary'):
                        _label = self.__label_for_iri(subj_iri)
                        with self.__nest(_h_tag, attrs={'class': 'Browse__heading'}):
                            with self.__nest_link(subj_iri):
                                self.__leaf('dfn', text=_label, attrs={'id': quote(subj_iri)})
                        _compact_focus = self.iri_shorthand.compact_iri(subj_iri)
                        if _compact_focus != _label:
                            self.__leaf('code', text=_compact_focus)
                        if _compact_focus != subj_iri:
                            self.__leaf('code', text=subj_iri)
                    self.__twoples(_twopledict)

    def __twoples(self, twopledict: primitive_rdf.RdfTwopleDictionary):
        with self.__nest('ul', {'class': 'Browse__twopleset'}):
            for _pred, _obj_set in shuffled(twopledict.items()):
                with self.__nest('li', {'class': 'Browse__twople'}, visible=True):
                    self.__leaf_link(_pred)
                    with self.__nest('ul', {'class': 'Browse__objectset'}):
                        for _obj in shuffled(_obj_set):
                            with self.__nest('li', {'class': 'Browse__object'}, visible=True):
                                self.__obj(_obj)

    def __obj(self, obj: primitive_rdf.RdfObject):
        if isinstance(obj, str):  # iri
            # TODO: detect whether indexcard?
            if obj in self.data.tripledict:
                if obj in self.__visiting_iris:
                    self.__leaf_link(obj)  # TODO: consider
                else:
                    self.__render_subj(obj)
            else:
                self.__leaf_link(obj)
        elif isinstance(obj, frozenset):  # blanknode
            if (RDF.type, RDF.Seq) in obj:
                self.__sequence(obj)
            else:
                self.__twoples(primitive_rdf.twopledict_from_twopleset(obj))
        elif isinstance(obj, primitive_rdf.Literal):
            self.__literal(obj)
        elif isinstance(obj, (float, int, datetime.date)):
            self.__literal(primitive_rdf.literal(obj))
        elif isinstance(obj, primitive_rdf.QuotedGraph):
            self.__quoted_graph(obj)

    def __literal(self, literal: primitive_rdf.Literal):
        # TODO language tag, datatypes
        _markdown_iri = primitive_rdf.iri_from_mediatype('text/markdown')
        _is_markdown = any(
            _datatype.startswith(_markdown_iri)
            for _datatype in literal.datatype_iris
        )
        # TODO: checksum_iri, literal_iri
        with self.__nest('article', attrs={'class': 'Browse__literal'}):
            if _is_markdown:
                # TODO: tests for safe_mode
                _html = markdown2.markdown(literal.unicode_value, safe_mode='escape')
                self.__current_element.append(etree_fromstring(f'<q>{_html}</q>'))
            else:
                self.__leaf('q', text=literal.unicode_value)
            for _datatype_iri in literal.datatype_iris:
                self.__leaf_link(_datatype_iri)

    def __sequence(self, sequence_twoples: frozenset):
        _obj_in_order = list(primitive_rdf.sequence_objects_in_order(sequence_twoples))
        with self.__nest('details', attrs={'open': ''}):
            self.__leaf('summary', text=str(len(_obj_in_order)))
            with self.__nest('ol'):  # TODO: style?
                for _seq_obj in _obj_in_order:
                    with self.__nest('li', visible=True):
                        self.__obj(_seq_obj)

    def __quoted_graph(self, quoted_graph: primitive_rdf.QuotedGraph):
        with self.__quoted_data(quoted_graph.tripledict):
            self.__render_subj(quoted_graph.focus_iri, start_collapsed=True)

    ###
    # private html-building helpers

    @contextlib.contextmanager
    def __rendering(self):
        # TODO: lang (according to request -- also translate)
        self.__current_element = Element('html')
        self.__visiting_iris = set()
        try:
            yield
            self.rendered_element = self.__current_element
        finally:
            self.__current_element = None
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
        self.data = primitive_rdf.RdfGraph(quoted_data)
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
        _parent_element = self.__current_element
        self.__current_element = SubElement(_parent_element, tag_name, _attrs)
        try:
            yield self.__current_element
        finally:
            self.__current_element = _parent_element

    def __leaf(self, tag_name, *, text=None, attrs=None):
        _leaf_element = SubElement(self.__current_element, tag_name, attrs or {})
        if text is not None:
            _leaf_element.text = text

    def __nest_link(self, iri: str, *, attrs=None):
        return self.__nest('a', attrs={
            **(attrs or {}),
            'href': self.__href_for_iri(iri),
        })

    def __leaf_link(self, iri: str, *, attrs=None):
        with self.__nest_link(iri, attrs=attrs) as _link:
            _link.text = self.iri_shorthand.compact_iri(iri)

    def __href_for_iri(self, iri: str):
        if self.http_request and (self.http_request.get_host() == urlsplit(iri).netloc):
            return iri
        return trove_browse_link(iri)

    def __label_for_iri(self, iri: str):
        # TODO: get actual label in requested language
        _shorthand = self.iri_shorthand.compact_iri(iri)
        return (
            get_sufficiently_unique_iri(iri)
            if _shorthand == iri
            else _shorthand
        )
