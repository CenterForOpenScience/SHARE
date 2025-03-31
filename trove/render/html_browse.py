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
from django.http import QueryDict
from django.urls import reverse
from primitive_metadata import primitive_rdf as rdf

from trove.util.iris import get_sufficiently_unique_iri
from trove.util.randomness import shuffled
from trove.vocab import mediatypes
from trove.vocab.namespaces import RDF, RDFS, SKOS, DCTERMS, FOAF, DC
from trove.vocab.static_vocab import combined_thesaurus__suffuniq
from trove.vocab.trove import trove_browse_link
from ._base import BaseRenderer

STABLE_MEDIATYPES = (mediatypes.JSONAPI,)
UNSTABLE_MEDIATYPES = (
    mediatypes.TURTLE,
    mediatypes.JSONLD,
    # TODO: below are only for search/index-card views
    mediatypes.JSON,
    mediatypes.TSV,
    mediatypes.CSV,
)

_LINK_TEXT_PREDICATES = (
    SKOS.prefLabel,
    RDFS.label,
    SKOS.altLabel,
    DCTERMS.title,
    DC.title,
    FOAF.name,
)


@dataclasses.dataclass
class RdfHtmlBrowseRenderer(BaseRenderer):
    MEDIATYPE = 'text/html; charset=utf-8'

    def simple_render_document(self) -> str:
        _html_builder = _HtmlBuilder(
            all_data=self.response_tripledict,
            focus_iri=self.response_focus.single_iri(),
            iri_shorthand=self.iri_shorthand,
        )
        _html_str = etree_tostring(_html_builder.html_element, encoding='unicode', method='html')
        return ''.join((
            '<!DOCTYPE html>',  # TODO: can etree put the doctype in?
            _html_str,
        ))


@dataclasses.dataclass
class _HtmlBuilder:
    all_data: rdf.RdfTripleDictionary
    focus_iri: str
    iri_shorthand: rdf.IriShorthand
    html_element: Element = dataclasses.field(init=False)
    __current_data: rdf.RdfTripleDictionary = dataclasses.field(init=False)
    __current_element: Element = dataclasses.field(init=False)
    __visiting_iris: set[str] = dataclasses.field(init=False)
    __heading_depth: int = 0

    def __post_init__(self):
        # TODO: lang (according to request -- also translate)
        self.html_element = self.__current_element = Element('html')
        self.__current_data = self.all_data
        self.__visiting_iris = set()
        with self.__nest('head'):
            self.__leaf('link', attrs={
                'rel': 'stylesheet',
                'href': staticfiles_storage.url('css/browse.css'),
            })
        _body_attrs = {
            'class': 'BrowseWrapper',
            'style': self._random_turn_style(),
        }
        with self.__nest('body', attrs=_body_attrs):
            self.__render_subj(self.focus_iri),
            self.__render_mediatype_links()
            self.__render_amalgamation_switch()
            # TODO: <details> with unvisited triples in self.data (unreachable from focus_iri)

    def __render_mediatype_links(self):
        with self.__nest_card():
            self.__leaf('header', text='alternate mediatypes')
            with self.__nest('ul', attrs={'class': 'Browse__twopleset'}):
                for _mediatype in shuffled((*STABLE_MEDIATYPES, *UNSTABLE_MEDIATYPES)):
                    with self.__nest('li', attrs={'class': 'Browse__twople'}):
                        self.__mediatype_link(_mediatype)

    def __render_amalgamation_switch(self):
        ...  # TODO
        # with self.__nest_card():
        #     _text = ('ON' if ... else 'OFF')
        #     self.__leaf('header', text=f'amalgamation {_text}')
        #     self.__leaf('a', text=..., attrs={
        #         'href': self._queryparam_href('withAmalgamation', ('' if ... else None)),
        #     })

    def __mediatype_link(self, mediatype: str):
        self.__leaf('a', text=mediatype, attrs={
            'href': self._queryparam_href('acceptMediatype', mediatype),
        })
        if mediatype in UNSTABLE_MEDIATYPES:
            self.__leaf('aside', text='(unstable)')
        if mediatype in STABLE_MEDIATYPES:
            with self.__nest('aside') as _aside:
                _aside.text = '(stable for '
                with self.__nest('a', attrs={'href': reverse('trove:docs')}) as _link:
                    _link.text = 'documented use'
                    _link.tail = ')'

    def __render_subj(self, subj_iri: str, start_collapsed=False):
        _twopledict = self.__current_data.get(subj_iri, {})
        with self.__visiting(subj_iri):
            with self.__h_tag() as _h_tag:
                with self.__nest_card('details'):
                    with self.__nest('summary'):
                        with self.__nest(_h_tag, attrs={'class': 'Browse__heading'}):
                            for _label in self.__link_texts_for_iri(subj_iri):
                                with self.__nest_link(subj_iri):
                                    self.__leaf('dfn', text=_label, attrs={'id': quote(subj_iri)})
                        _compact_focus = self.iri_shorthand.compact_iri(subj_iri)
                        if _compact_focus != _label:
                            self.__leaf('code', text=_compact_focus)
                        if _compact_focus != subj_iri:
                            self.__leaf('code', text=subj_iri)
                    self.__twoples(_twopledict)

    def __twoples(self, twopledict: rdf.RdfTwopleDictionary):
        with self.__nest('ul', {'class': 'Browse__twopleset'}):
            for _pred, _obj_set in shuffled(twopledict.items()):
                with self.__nest('li', {'class': 'Browse__twople'}):
                    self.__leaf_link(_pred)
                    with self.__nest('ul', {'class': 'Browse__objectset'}):
                        for _obj in shuffled(_obj_set):
                            with self.__nest('li', {'class': 'Browse__object'}):
                                self.__obj(_obj)

    def __obj(self, obj: rdf.RdfObject):
        if isinstance(obj, str):  # iri
            # TODO: detect whether indexcard?
            if obj in self.__current_data:
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
                self.__twoples(rdf.twopledict_from_twopleset(obj))
        elif isinstance(obj, rdf.Literal):
            self.__literal(obj)
        elif isinstance(obj, (float, int, datetime.date)):
            self.__literal(rdf.literal(obj))
        elif isinstance(obj, rdf.QuotedGraph):
            self.__quoted_graph(obj)

    def __literal(self, literal: rdf.Literal):
        # TODO language tag, datatypes
        _markdown_iri = rdf.iri_from_mediatype('text/markdown')
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
                self.__leaf('q', text=literal)
            for _datatype_iri in literal.datatype_iris:
                self.__leaf_link(_datatype_iri)

    def __sequence(self, sequence_twoples: frozenset):
        _obj_in_order = list(rdf.sequence_objects_in_order(sequence_twoples))
        with self.__nest('details', attrs={'open': ''}):
            self.__leaf('summary', text=str(len(_obj_in_order)))
            with self.__nest('ol'):  # TODO: style?
                for _seq_obj in _obj_in_order:
                    with self.__nest('li'):  # , visible=True):
                        self.__obj(_seq_obj)

    def __quoted_graph(self, quoted_graph: rdf.QuotedGraph):
        with self.__quoted_data(quoted_graph.tripledict):
            self.__render_subj(quoted_graph.focus_iri, start_collapsed=True)

    ###
    # private html-building helpers

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
        _outer_data = self.__current_data
        _outer_visiting_iris = self.__visiting_iris
        self.__current_data = quoted_data
        self.__visiting_iris = set()
        try:
            yield
        finally:
            self.__current_data = _outer_data
            self.__visiting_iris = _outer_visiting_iris

    @contextlib.contextmanager
    def __nest(self, tag_name, attrs=None):
        _attrs = {**attrs} if attrs else {}
        _parent_element = self.__current_element
        self.__current_element = SubElement(_parent_element, tag_name, _attrs)
        try:
            yield self.__current_element
        finally:
            self.__current_element = _parent_element

    def __leaf(self, tag_name, *, text=None, attrs=None):
        _leaf_element = SubElement(self.__current_element, tag_name, attrs or {})
        if isinstance(text, rdf.Literal):
            # TODO: lang
            _leaf_element.text = text.unicode_value
        elif text is not None:
            _leaf_element.text = text

    def __nest_link(self, iri: str, *, attrs=None):
        return self.__nest('a', attrs={
            **(attrs or {}),
            'href': trove_browse_link(iri),
        })

    def __leaf_link(self, iri: str, *, attrs=None):
        for _text in self.__link_texts_for_iri(iri):
            with self.__nest_link(iri, attrs=attrs) as _link:
                # TODO: lang
                _link.text = (
                    _text.unicode_value
                    if isinstance(_text, rdf.Literal)
                    else _text
                )

    def __nest_card(self, tag: str = 'nav', start_collapsed=False):
        return self.__nest(
            tag,
            attrs={
                'class': 'Browse__card',
                'style': self._random_turn_style(),
                **({} if start_collapsed else {'open': ''}),
            },
        )

    def __link_texts_for_iri(self, iri: str):
        # TODO: consider requested language
        _suffuniq = get_sufficiently_unique_iri(iri)
        _thesaurus_entry = combined_thesaurus__suffuniq().get(_suffuniq)
        if _thesaurus_entry:
            for _pred in _LINK_TEXT_PREDICATES:
                _objects = _thesaurus_entry.get(_pred)
                if _objects:
                    return _objects
        _shorthand = self.iri_shorthand.compact_iri(iri)
        return (
            [_suffuniq]
            if _shorthand == iri
            else [_shorthand]
        )

    def _random_turn_style(self):
        return f'--random-turn: {random.random()}turn;'

    def _queryparam_href(self, param_name: str, param_value: str | None):
        (_scheme, _netloc, _path, _query, _fragment) = urlsplit(self.focus_iri)
        _qparams = QueryDict(_query, mutable=True)
        if param_value is None:
            del _qparams[param_name]
        else:
            _qparams[param_name] = param_value
        return urlunsplit((
            _scheme,
            _netloc,
            _path,
            _qparams.urlencode(),
            _fragment,
        ))
