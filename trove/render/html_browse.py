import contextlib
import dataclasses
import datetime
import math
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
import markdown2
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
_IMPLICIT_DATATYPES = frozenset((
    RDF.string,
    RDF.langString,
))

_PHI = (math.sqrt(5) + 1) / 2


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
    __last_hue_turn: float = dataclasses.field(default_factory=random.random)

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
            'style': self._hue_turn_css(),
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

    def __render_subj(self, subj_iri: str, *, start_collapsed=True):
        _twopledict = self.__current_data.get(subj_iri, {})
        with self.__visiting(subj_iri):
            with self.__nest_card('article'):
                with self.__nest('header'):
                    _compact = self.iri_shorthand.compact_iri(subj_iri)
                    _suffuniq = get_sufficiently_unique_iri(subj_iri)
                    _h_text = (_compact if (_compact != subj_iri) else _suffuniq)
                    with self.__nest_h_tag():
                        self.__leaf('dfn', text=_h_text, attrs={'id': quote(subj_iri)})
                    if _compact not in (subj_iri, _h_text):
                        self.__leaf('code', text=_compact)
                    if _suffuniq != _h_text:
                        self.__leaf('code', text=_suffuniq)
                    for _label in self.__labels_for_iri(subj_iri):
                        self.__literal(_label)
                if _twopledict:
                    with self.__nest_card('details') as _details:
                        if not start_collapsed:
                            _details['open'] = ''
                        self.__leaf('summary', text='details...')
                        self.__twoples(_twopledict)

    def __twoples(self, twopledict: rdf.RdfTwopleDictionary):
        with self.__nest('dl', {'class': 'Browse__twopleset'}):
            for _pred, _obj_set in shuffled(twopledict.items()):
                with self.__nest('dt'):
                    self.__compact_link(_pred)
                    for _text in self.__labels_for_iri(_pred):
                        self.__literal(_text)
                with self.__nest('dd'):
                    for _obj in shuffled(_obj_set):
                        self.__obj(_obj)
        # with self.__nest('ul', {'class': 'Browse__twopleset'}):
        #     for _pred, _obj_set in shuffled(twopledict.items()):
        #         with self.__nest('li', {'class': 'Browse__twople'}):
        #             self.__leaf_link(_pred)
        #             with self.__nest('ul', {'class': 'Browse__objectset'}):
        #                 for _obj in shuffled(_obj_set):
        #                     with self.__nest('li', {'class': 'Browse__object'}):
        #                         self.__obj(_obj)

    def __obj(self, obj: rdf.RdfObject):
        if isinstance(obj, str):  # iri
            # TODO: detect whether indexcard?
            if obj in self.__current_data:
                if obj in self.__visiting_iris:
                    self.__iri_link_and_labels(obj)  # TODO: consider
                else:
                    self.__render_subj(obj)
            else:
                self.__iri_link_and_labels(obj)
        elif isinstance(obj, frozenset):  # blanknode
            if (RDF.type, RDF.Seq) in obj:
                self.__sequence(obj)
            else:
                self.__blanknode(obj)
        elif isinstance(obj, rdf.Literal):
            self.__literal(obj)
        elif isinstance(obj, (float, int, datetime.date)):
            self.__literal(rdf.literal(obj))
        elif isinstance(obj, rdf.QuotedGraph):
            self.__quoted_graph(obj)

    def __literal(self, literal: rdf.Literal | str):
        _lit = (literal if isinstance(literal, rdf.Literal) else rdf.literal(literal))
        _markdown_iri = rdf.iri_from_mediatype('text/markdown')
        _is_markdown = any(
            _datatype.startswith(_markdown_iri)
            for _datatype in _lit.datatype_iris
        )
        # TODO: checksum_iri, literal_iri
        with self.__nest('article', attrs={'class': 'Browse__literal'}):
            if _is_markdown:
                # TODO: tests for safe_mode
                _html = markdown2.markdown(_lit.unicode_value, safe_mode='escape')
                self.__current_element.append(etree_fromstring(f'<q>{_html}</q>'))
            else:
                self.__leaf('q', text=_lit)
            for _datatype_iri in _lit.datatype_iris.difference(_IMPLICIT_DATATYPES):
                self.__compact_link(_datatype_iri)

    def __sequence(self, sequence_twoples: frozenset):
        _obj_in_order = list(rdf.sequence_objects_in_order(sequence_twoples))
        with self.__nest('details', attrs={'open': ''}):
            self.__leaf('summary', text=f'sequence of {len(_obj_in_order)}')
            with self.__nest('ol'):  # TODO: style?
                for _seq_obj in _obj_in_order:
                    with self.__nest('li'):  # , visible=True):
                        self.__obj(_seq_obj)

    def __quoted_graph(self, quoted_graph: rdf.QuotedGraph):
        with self.__quoted_data(quoted_graph.tripledict):
            self.__render_subj(quoted_graph.focus_iri, start_collapsed=True)

    def __blanknode(self, blanknode: rdf.RdfTwopleDictionary | frozenset):
        _twopledict = (
            blanknode
            if isinstance(blanknode, dict)
            else rdf.twopledict_from_twopleset(blanknode)
        )
        with self.__nest('article', attrs={'class': 'Browse__blanknode'}):
            self.__twoples(_twopledict)

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
    def __nest_h_tag(self, **kwargs):
        _outer_heading_depth = self.__heading_depth
        if not _outer_heading_depth:
            self.__heading_depth = 1
        elif _outer_heading_depth < 6:  # h6 deepest
            self.__heading_depth += 1
        _h_tag = f'h{self.__heading_depth}'
        with self.__nest(_h_tag, **kwargs) as _nested:
            try:
                yield _nested
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

    def __browse_link(self, iri: str, *, attrs=None):
        return self.__nest('a', attrs={
            **(attrs or {}),
            'href': trove_browse_link(iri),
        })

    def __iri_link_and_labels(self, iri: str):
        self.__compact_link(iri)
        for _text in self.__labels_for_iri(iri):
            self.__literal(_text)

    def __compact_link(self, iri: str):
        _compact = self.iri_shorthand.compact_iri(iri)
        with self.__browse_link(iri) as _link:
            _link.text = _compact

    def __nest_card(self, tag: str = 'nav'):
        return self.__nest(
            tag,
            attrs={
                'class': 'Browse__card',
                'style': self._hue_turn_css(),
            },
        )

    def __labels_for_iri(self, iri: str):
        # TODO: consider requested language
        _suffuniq = get_sufficiently_unique_iri(iri)
        _thesaurus_entry = combined_thesaurus__suffuniq().get(_suffuniq)
        if _thesaurus_entry:
            for _pred in _LINK_TEXT_PREDICATES:
                yield from shuffled(_thesaurus_entry.get(_pred, ()))

    def _hue_turn_css(self):
        # return f'--hue-turn: {random.random()}turn;'
        _hue_turn = self.__last_hue_turn + (_PHI / 13)
        self.__last_hue_turn = _hue_turn
        return f'--hue-turn: {_hue_turn}turn;'

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
