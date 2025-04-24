from collections.abc import Iterator
import contextlib
import dataclasses
import datetime
import math
import random
import re
from typing import ClassVar
from urllib.parse import quote, urlsplit, urlunsplit
from xml.etree.ElementTree import (
    Element,
    tostring as etree_tostring,
    fromstring as etree_fromstring,
)

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.http import QueryDict
from django.urls import reverse
from django.utils.translation import gettext as _
import markdown2
from primitive_metadata import primitive_rdf as rdf

from trove.util.iris import get_sufficiently_unique_iri
from trove.util.randomness import shuffled
from trove.vocab import mediatypes
from trove.vocab.namespaces import RDF, RDFS, SKOS, DCTERMS, FOAF, DC
from trove.vocab.static_vocab import combined_thesaurus__suffuniq
from trove.vocab.trove import trove_browse_link
from ._base import BaseRenderer
from ._html import HtmlBuilder

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

_QUERYPARAM_SPLIT_RE = re.compile(r'(?=[?&])')

_PHI = (math.sqrt(5) + 1) / 2

_HTML_DOCTYPE = '<!DOCTYPE html>'


@dataclasses.dataclass
class RdfHtmlBrowseRenderer(BaseRenderer):
    MEDIATYPE: ClassVar[str] = 'text/html; charset=utf-8'
    __current_data: rdf.RdfTripleDictionary = dataclasses.field(init=False)
    __visiting_iris: set[str] = dataclasses.field(init=False)
    __hb: HtmlBuilder = dataclasses.field(init=False)
    __last_hue_turn: float = dataclasses.field(default_factory=random.random)

    def __post_init__(self):
        # TODO: lang (according to request -- also translate)
        self.__current_data = self.response_tripledict
        self.__visiting_iris = set()

    @property
    def is_data_blended(self) -> bool | None:
        return self.response_gathering.gatherer_kwargs.get('blend_cards')

    # override BaseRenderer
    def simple_render_document(self) -> str:
        self.__hb = HtmlBuilder(Element('html'))
        self.render_html_head()
        _body_attrs = {
            'class': 'BrowseWrapper',
            'style': self._hue_turn_css(),
        }
        with self.__hb.nest('body', attrs=_body_attrs):
            self.render_nav()
            self.render_main()
            self.render_footer()
        return '\n'.join((
            _HTML_DOCTYPE,
            etree_tostring(self.__hb.root_element, encoding='unicode', method='html'),
        ))

    def render_html_head(self):
        with self.__hb.nest('head'):
            self.__hb.leaf('link', attrs={
                'rel': 'stylesheet',
                'href': staticfiles_storage.url('css/browse.css'),
            })

    def render_nav(self):
        with self.__hb.nest('nav'):
            self.__alternate_mediatypes_card()
            if self.is_data_blended is not None:
                self.__blender_toggle_card()

    def render_main(self):
        with self.__hb.nest('main'):
            for _iri in self.response_focus.iris:
                self.__render_subj(_iri)
            # TODO: show additional unvisited triples?

    def render_footer(self):
        with self.__hb.nest('footer'):
            ...

    def __alternate_mediatypes_card(self):
        with self.__nest_card('details'):
            self.__hb.leaf('summary', text=_('alternate mediatypes'))
            for _mediatype in shuffled((*STABLE_MEDIATYPES, *UNSTABLE_MEDIATYPES)):
                with self.__hb.nest('span', attrs={'class': 'Browse__literal'}):
                    self.__mediatype_link(_mediatype)

    def __blender_toggle_card(self):
        with self.__nest_card('details'):
            if self.is_data_blended:
                _header_text = _('card-blending ON')
                _link_text = _('disable card-blending')
                _link_blend: str | None = None  # remove blendCards param (defaults false)
            else:
                _header_text = _('card-blending OFF')
                _link_text = _('enable card-blending')
                _link_blend = '1'  # blendCards=1
            self.__hb.leaf('summary', text=_header_text)
            self.__hb.leaf('a', text=_link_text, attrs={
                'href': self._queryparam_href('blendCards', _link_blend),
            })

    def __mediatype_link(self, mediatype: str):
        self.__hb.leaf('a', text=mediatype, attrs={
            'href': self._queryparam_href('acceptMediatype', mediatype),
        })
        if mediatype in UNSTABLE_MEDIATYPES:
            self.__hb.leaf('aside', text=_('(unstable)'))
        if mediatype in STABLE_MEDIATYPES:
            with self.__hb.nest('aside'):
                with self.__hb.nest('a', attrs={'href': reverse('trove:docs')}) as _link:
                    _link.text = _('(stable for documented use)')

    def __render_subj(self, subj_iri: str, *, start_collapsed=None):
        _twopledict = self.__current_data.get(subj_iri, {})
        with self.__visiting(subj_iri):
            with self.__nest_card('article'):
                with self.__hb.nest('header'):
                    _compact = self.iri_shorthand.compact_iri(subj_iri)
                    _is_compactable = (_compact != subj_iri)
                    _should_link = (subj_iri not in self.response_focus.iris)
                    with self.__hb.nest_h_tag(attrs={'id': quote(subj_iri)}) as _h:
                        if _should_link:
                            with self.__nest_link(subj_iri) as _link:
                                if _is_compactable:
                                    _link.text = _compact
                                else:
                                    self.__split_iri_pre(subj_iri)
                        else:
                            if _is_compactable:
                                _h.text = _compact
                            else:
                                self.__split_iri_pre(subj_iri)
                    self.__iri_subheaders(subj_iri)
                if _twopledict:
                    with self.__hb.nest('details') as _details:
                        _detail_depth = sum((_el.tag == 'details') for _el in self.__hb._nested_elements)
                        _should_open = (
                            _detail_depth < 3
                            if start_collapsed is None
                            else not start_collapsed
                        )
                        if _should_open:
                            _details.set('open', '')
                        self.__hb.leaf('summary', text=_('more details...'))
                        self.__twoples(_twopledict)

    def __twoples(self, twopledict: rdf.RdfTwopleDictionary):
        with self.__hb.nest('dl', {'class': 'Browse__twopleset'}):
            for _pred, _obj_set in shuffled(twopledict.items()):
                with self.__hb.nest('dt', attrs={'class': 'Browse__predicate'}):
                    self.__compact_link(_pred)
                    for _text in self.__iri_thesaurus_labels(_pred):
                        self.__literal(_text)
                with self.__hb.nest('dd'):
                    for _obj in shuffled(_obj_set):
                        self.__obj(_obj)

    def __obj(self, obj: rdf.RdfObject):
        if isinstance(obj, str):  # iri
            # TODO: detect whether indexcard?
            if (obj in self.__current_data) and (obj not in self.__visiting_iris):
                self.__render_subj(obj)
            else:
                with self.__hb.nest('article', attrs={'class': 'Browse__object'}):
                    self.__iri_link_and_labels(obj)
        elif isinstance(obj, frozenset):  # blanknode
            if (RDF.type, RDF.Seq) in obj:
                self.__sequence(obj)
            else:
                self.__blanknode(obj)
        elif isinstance(obj, rdf.Literal):
            self.__literal(obj, is_rdf_object=True)
        elif isinstance(obj, (float, int, datetime.date)):
            self.__literal(rdf.literal(obj), is_rdf_object=True)
        elif isinstance(obj, rdf.QuotedGraph):
            self.__quoted_graph(obj)

    def __literal(
        self,
        literal: rdf.Literal | str,
        *,
        is_rdf_object: bool = False,
    ):
        _lit = (literal if isinstance(literal, rdf.Literal) else rdf.literal(literal))
        _markdown_iri = rdf.iri_from_mediatype('text/markdown')
        _is_markdown = any(
            _datatype.startswith(_markdown_iri)
            for _datatype in _lit.datatype_iris
        )
        _element_classes = ['Browse__literal']
        if is_rdf_object:
            _element_classes.append('Browse__object')
        # TODO: checksum_iri, literal_iri
        with self.__hb.nest('article', attrs={'class': ' '.join(_element_classes)}):
            for _datatype_iri in _lit.datatype_iris.difference(_IMPLICIT_DATATYPES):
                self.__compact_link(_datatype_iri)
            if _is_markdown:
                # TODO: tests for safe_mode
                _html = markdown2.markdown(_lit.unicode_value, safe_mode='escape')
                self.__hb._current_element.append(etree_fromstring(f'<q>{_html}</q>'))
            else:
                self.__hb.leaf('q', text=_lit)

    def __sequence(self, sequence_twoples: frozenset):
        _obj_in_order = list(rdf.sequence_objects_in_order(sequence_twoples))
        with self.__hb.nest('details', attrs={'open': '', 'class': 'Browse__blanknode Browse__object'}):
            _text = _('sequence of %(count)s') % {'count': len(_obj_in_order)}
            self.__hb.leaf('summary', text=_text)
            with self.__hb.nest('ol'):  # TODO: style?
                for _seq_obj in _obj_in_order:
                    with self.__hb.nest('li'):  # , visible=True):
                        self.__obj(_seq_obj)

    def __quoted_graph(self, quoted_graph: rdf.QuotedGraph):
        with self.__quoted_data(quoted_graph.tripledict):
            self.__render_subj(quoted_graph.focus_iri)  # , start_collapsed=True)

    def __blanknode(self, blanknode: rdf.RdfTwopleDictionary | frozenset):
        _twopledict = (
            blanknode
            if isinstance(blanknode, dict)
            else rdf.twopledict_from_twopleset(blanknode)
        )
        with self.__hb.nest('details', attrs={
            'open': '',
            'class': 'Browse__blanknode Browse__object',
            'style': self._hue_turn_css(),
        }):
            self.__hb.leaf('summary', text='(blank node)')
            self.__twoples(_twopledict)

    def __split_iri_pre(self, iri: str):
        self.__hb.leaf('pre', text='\n'.join(self.__iri_lines(iri)))

    @contextlib.contextmanager
    def __visiting(self, iri: str):
        assert iri not in self.__visiting_iris
        self.__visiting_iris.add(iri)
        try:
            yield
        finally:
            self.__visiting_iris.remove(iri)

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

    def __iri_link_and_labels(self, iri: str):
        self.__compact_link(iri)
        for _text in self.__iri_thesaurus_labels(iri):
            self.__literal(_text)

    def __nest_link(self, iri: str):
        _href = (
            iri
            if _is_local_url(iri)
            else trove_browse_link(iri)
        )
        return self.__hb.nest('a', attrs={'href': _href})

    def __compact_link(self, iri: str):
        with self.__nest_link(iri) as _a:
            _a.text = self.iri_shorthand.compact_iri(iri)
        return _a

    def __nest_card(self, tag: str):
        return self.__hb.nest(
            tag,
            attrs={
                'class': 'Browse__card',
                'style': self._hue_turn_css(),
            },
        )

    def __iri_thesaurus_labels(self, iri: str):
        # TODO: consider requested language
        _labels: set[rdf.RdfObject] = set()
        _suffuniq = get_sufficiently_unique_iri(iri)
        _thesaurus_entry = combined_thesaurus__suffuniq().get(_suffuniq)
        if _thesaurus_entry:
            for _pred in _LINK_TEXT_PREDICATES:
                _labels.update(_thesaurus_entry.get(_pred, ()))
        _twoples = self.__current_data.get(iri)
        if _twoples:
            for _pred in _LINK_TEXT_PREDICATES:
                _labels.update(_twoples.get(_pred, ()))
        return shuffled(_labels)

    def _hue_turn_css(self):
        _hue_turn = (self.__last_hue_turn + _PHI) % 1.0
        self.__last_hue_turn = _hue_turn
        return f'--hue-turn: {_hue_turn}turn;'

    def _queryparam_href(self, param_name: str, param_value: str | None):
        _base_url = self.response_focus.single_iri()
        if not _is_local_url(_base_url):
            _base_url = trove_browse_link(_base_url)
        (_scheme, _netloc, _path, _query, _fragment) = urlsplit(_base_url)
        _qparams = QueryDict(_query, mutable=True)
        if param_value is None:
            try:
                del _qparams[param_name]
            except KeyError:
                pass
        else:
            _qparams[param_name] = param_value
        return urlunsplit((
            _scheme,
            _netloc,
            _path,
            _qparams.urlencode(),
            _fragment,
        ))

    def __iri_subheaders(self, iri: str) -> None:
        _type_iris = self.__current_data.get(iri, {}).get(RDF.type, ())
        if _type_iris:
            for _type_iri in _type_iris:
                self.__compact_link(_type_iri)
        _labels = self.__iri_thesaurus_labels(iri)
        if _labels:
            for _label in _labels:
                self.__literal(_label)

    def __iri_lines(self, iri: str) -> Iterator[str]:
        (_scheme, _netloc, _path, _query, _fragment) = urlsplit(iri)
        yield (
            f'://{_netloc}{_path}'
            if _netloc
            else f'{_scheme}:{_path}'
        )
        if _query:
            yield from filter(bool, _QUERYPARAM_SPLIT_RE.split(f'?{_query}'))
        if _fragment:
            yield f'#{_fragment}'


def _append_class(el: Element, element_class: str):
    el.set(
        'class',
        ' '.join(filter(None, (element_class, el.get('class')))),
    )


def _is_local_url(iri: str) -> bool:
    return iri.startswith(settings.SHARE_WEB_URL)
