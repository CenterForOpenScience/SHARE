from collections.abc import Generator
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
    fromstring as etree_fromstring,
)

from django.contrib.staticfiles.storage import staticfiles_storage
from django.http import QueryDict
from django.urls import reverse
from django.utils.translation import gettext as _
import markdown2
from primitive_metadata import primitive_rdf as rdf

from trove.links import (
    trove_browse_link,
    is_local_url,
)
from trove.util.html import HtmlBuilder
from trove.util.iris import get_sufficiently_unique_iri
from trove.util.randomness import shuffled
from trove.vocab import mediatypes
from trove.vocab import jsonapi
from trove.vocab.namespaces import RDF, RDFS, SKOS, DCTERMS, FOAF, DC, OSFMAP, TROVE
from trove.vocab.static_vocab import combined_thesaurus__suffuniq
from ._base import BaseRenderer
from .rendering import (
    EntireRendering,
    ProtoRendering,
)

STABLE_MEDIATYPES = (mediatypes.JSONAPI,)
UNSTABLE_MEDIATYPES = (
    mediatypes.TURTLE,
    mediatypes.JSONLD,
    # TODO: below are only for search/index-card views
    mediatypes.JSON,
    mediatypes.TSV,
    mediatypes.CSV,
)
SEARCHONLY_MEDIATYPES = frozenset((
    mediatypes.JSON,
    mediatypes.TSV,
    mediatypes.CSV,
))

_LINK_TEXT_PREDICATES = (
    SKOS.prefLabel,
    RDFS.label,
    SKOS.altLabel,
    DCTERMS.title,
    DC.title,
    FOAF.name,
    OSFMAP.fileName,
)
_IMPLICIT_DATATYPES = frozenset((
    RDF.string,
    RDF.langString,
))
_PREDICATES_RENDERED_SPECIAL = frozenset((
    RDF.type,
))
_PRIMITIVE_LITERAL_TYPES = (float, int, datetime.date)

_QUERYPARAM_SPLIT_RE = re.compile(r'(?=[?&])')

_PHI = (math.sqrt(5) + 1) / 2


@dataclasses.dataclass
class RdfHtmlBrowseRenderer(BaseRenderer):
    MEDIATYPE: ClassVar[str] = mediatypes.HTML
    __current_data: rdf.RdfGraph = dataclasses.field(init=False)
    __visiting_iris: set[str] = dataclasses.field(init=False)
    __hb: HtmlBuilder = dataclasses.field(init=False)
    __last_hue_turn: float = dataclasses.field(default_factory=random.random)

    def __post_init__(self) -> None:
        # TODO: lang (according to request -- also translate)
        self.__current_data = self.response_data
        self.__visiting_iris = set()

    @property
    def is_data_blended(self) -> bool | None:
        return self.response_gathering.gatherer_kwargs.get('blend_cards')

    @property
    def is_search(self) -> bool:
        return not self.response_focus.type_iris.isdisjoint((
            TROVE.Cardsearch,
            TROVE.Valuesearch,
        ))

    # override BaseRenderer
    def render_document(self) -> ProtoRendering:
        return EntireRendering(self.MEDIATYPE, self.render_html_str())

    def render_html_str(self) -> str:
        self.__hb = HtmlBuilder()
        self.render_html_head()
        with (
            self._hue_turn_css() as _hue_turn_style,
            self.__hb.nest('body', attrs={
                'class': 'BrowseWrapper',
                'style': _hue_turn_style,
            }),
        ):
            self.render_nav()
            self.render_main()
            self.render_footer()
        return self.__hb.as_html_doc()

    def render_html_head(self) -> None:
        with self.__hb.nest('head'):
            self.__hb.leaf('link', attrs={
                'rel': 'stylesheet',
                'href': staticfiles_storage.url('css/browse.css'),
            })

    def render_nav(self) -> None:
        with self.__hb.nest('nav'):
            self.__alternate_mediatypes_card()
            if self.is_data_blended is not None:
                self.__blender_toggle_card()

    def render_main(self) -> None:
        with self.__hb.nest('main'):
            for _iri in self.response_focus.iris:
                self.__render_subj(_iri)
            # TODO: show additional unvisited triples?

    def render_footer(self) -> None:
        with self.__hb.nest('footer'):
            ...

    def __alternate_mediatypes_card(self) -> None:
        with self.__nest_card('details'):
            self.__hb.leaf('summary', text=_('alternate mediatypes'))
            _linked_mediatypes = {*STABLE_MEDIATYPES, *UNSTABLE_MEDIATYPES}
            if not self.is_search:
                _linked_mediatypes -= SEARCHONLY_MEDIATYPES
            for _mediatype in shuffled(_linked_mediatypes):
                with self.__hb.nest('span', attrs={'class': 'Browse__literal'}):
                    self.__mediatype_link(_mediatype)

    def __blender_toggle_card(self) -> None:
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

    def __mediatype_link(self, mediatype: str) -> None:
        self.__hb.leaf('a', text=mediatype, attrs={
            'href': self._queryparam_href('acceptMediatype', mediatype),
        })
        if mediatype in UNSTABLE_MEDIATYPES:
            self.__hb.leaf('aside', text=_('(unstable)'))
        if mediatype in STABLE_MEDIATYPES:
            with self.__hb.nest('aside'):
                with self.__hb.nest('a', attrs={'href': reverse('trove:docs')}) as _link:
                    _link.text = _('(stable for documented use)')

    def __render_subj(self, subj_iri: str, *, include_details: bool = True) -> None:
        with self.__visiting(subj_iri) as _h_tag:
            with self.__nest_card('article'):
                with self.__hb.nest('header'):
                    with self.__hb.nest(_h_tag, attrs={'id': quote(subj_iri)}):
                        if self.__is_focus(subj_iri):
                            self.__split_iri_pre(subj_iri)
                        else:
                            with self.__nest_link(subj_iri):
                                self.__split_iri_pre(subj_iri)
                    self.__iri_subheaders(subj_iri)
                    if self.__is_focus(subj_iri):
                        self.__hb.leaf('pre', text=subj_iri)
                if include_details and (_twopledict := self.__current_data.tripledict.get(subj_iri, {})):
                    _details_attrs = (
                        {'open': ''}
                        if (self.__is_focus(subj_iri) or is_local_url(subj_iri))
                        else {}
                    )
                    with self.__hb.nest('details', _details_attrs):
                        self.__hb.leaf('summary', text=_('more details...'))
                        self.__twoples(_twopledict)

    def __twoples(self, twopledict: rdf.RdfTwopleDictionary) -> None:
        with self.__hb.nest('dl', {'class': 'Browse__twopleset'}):
            for _pred, _obj_set in self.__order_twopledict(twopledict):
                with self.__hb.nest('dt', attrs={'class': 'Browse__predicate'}):
                    self.__compact_link(_pred)
                    for _text in self.__iri_thesaurus_labels(_pred):
                        self.__literal(_text)
                with self.__hb.nest('dd'):
                    for _obj in _obj_set:
                        self.__obj(_obj)

    def __order_twopledict(self, twopledict: rdf.RdfTwopleDictionary) -> Generator[tuple[str, list[rdf.RdfObject]]]:
        _items_with_sorted_objs = (
            (_pred, sorted(_obj_set, key=_obj_ordering_key))
            for _pred, _obj_set in twopledict.items()
            if _pred not in _PREDICATES_RENDERED_SPECIAL
        )
        yield from sorted(
            _items_with_sorted_objs,
            key=lambda _item: _obj_ordering_key(_item[1][0]),
        )

    def __obj(self, obj: rdf.RdfObject) -> None:
        if isinstance(obj, str):  # iri
            # TODO: detect whether indexcard?
            if (obj in self.__current_data.tripledict) and (obj not in self.__visiting_iris):
                self.__render_subj(obj)
            else:
                with self.__hb.nest('article', attrs={'class': 'Browse__object'}):
                    self.__iri_link_and_labels(obj)
        elif isinstance(obj, frozenset):  # blanknode
            if _is_jsonapi_link_obj(obj):
                self.__jsonapi_link_obj(obj)
            elif _is_sequence_obj(obj):
                self.__sequence(obj)
            else:
                self.__blanknode(obj)
        elif isinstance(obj, rdf.Literal):
            self.__literal(obj, is_rdf_object=True)
        elif isinstance(obj, _PRIMITIVE_LITERAL_TYPES):
            self.__literal(rdf.literal(obj), is_rdf_object=True)
        elif isinstance(obj, rdf.QuotedGraph):
            self.__quoted_graph(obj)

    def __literal(
        self,
        literal: rdf.Literal | str,
        *,
        is_rdf_object: bool = False,
    ) -> None:
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
                self.__hb.current_element.append(etree_fromstring(f'<q>{_html}</q>'))
            else:
                self.__hb.leaf('q', text=_lit)

    def __sequence(self, sequence_twoples: frozenset[rdf.RdfTwople]) -> None:
        _obj_in_order = list(rdf.sequence_objects_in_order(sequence_twoples))
        with self.__hb.nest('details', attrs={'open': '', 'class': 'Browse__blanknode Browse__object'}):
            _text = _('sequence of %(count)s') % {'count': len(_obj_in_order)}
            self.__hb.leaf('summary', text=_text)
            with self.__hb.nest('ol'):  # TODO: style?
                for _seq_obj in _obj_in_order:
                    with self.__hb.nest('li'):  # , visible=True):
                        self.__obj(_seq_obj)

    def __quoted_graph(self, quoted_graph: rdf.QuotedGraph) -> None:
        _should_include_details = (
            self.__is_focus(quoted_graph.focus_iri)
            or ((  # primary topic of response focus
                self.response_focus.single_iri(),
                FOAF.primaryTopic,
                quoted_graph.focus_iri,
            ) in self.response_data)
        )
        with self.__quoted_data(quoted_graph):
            self.__render_subj(quoted_graph.focus_iri, include_details=_should_include_details)

    def __blanknode(self, blanknode: rdf.RdfTwopleDictionary | frozenset) -> None:
        _twopledict = (
            blanknode
            if isinstance(blanknode, dict)
            else rdf.twopledict_from_twopleset(blanknode)
        )
        with (
            self._hue_turn_css() as _hue_turn_style,
            self.__hb.nest('details', attrs={
                'open': '',
                'class': 'Browse__blanknode Browse__object',
                'style': _hue_turn_style,
            }),
        ):
            with self.__hb.nest('summary'):
                for _type_iri in _twopledict.get(RDF.type, ()):
                    self.__compact_link(_type_iri)
            self.__twoples(_twopledict)

    def __jsonapi_link_obj(self, twopleset: frozenset[rdf.RdfTwople]) -> None:
        _iri = next(
            (str(_obj) for (_pred, _obj) in twopleset if _pred == RDF.value),
            '',
        )
        _text = next(
            (_obj.unicode_value for (_pred, _obj) in twopleset if _pred == jsonapi.JSONAPI_MEMBERNAME),
            '',
        )
        with self.__nest_link(_iri, attrs={'class': 'Browse__blanknode Browse__object'}) as _a:
            _a.text = _('link: %(linktext)s') % {'linktext': _text}

    def __split_iri_pre(self, iri: str) -> None:
        self.__hb.leaf('pre', text='\n'.join(self.__iri_display_lines(iri)))

    @contextlib.contextmanager
    def __visiting(self, iri: str) -> Generator[str]:
        assert iri not in self.__visiting_iris
        self.__visiting_iris.add(iri)
        try:
            with self.__hb.deeper_heading() as _h_tag:
                yield _h_tag
        finally:
            self.__visiting_iris.remove(iri)

    @contextlib.contextmanager
    def __quoted_data(self, quoted_data: rdf.RdfGraph) -> Generator[None]:
        _outer_data = self.__current_data
        _outer_visiting_iris = self.__visiting_iris
        self.__current_data = quoted_data
        self.__visiting_iris = set()
        try:
            yield
        finally:
            self.__current_data = _outer_data
            self.__visiting_iris = _outer_visiting_iris

    def __iri_link_and_labels(self, iri: str) -> None:
        self.__compact_link(iri)
        for _text in self.__iri_thesaurus_labels(iri):
            self.__literal(_text)

    def __nest_link(self, iri: str, attrs: dict[str, str] | None = None) -> contextlib.AbstractContextManager[Element]:
        _href = (
            iri
            if is_local_url(iri)
            else trove_browse_link(iri)
        )
        return self.__hb.nest('a', attrs={**(attrs or {}), 'href': _href})

    def __compact_link(self, iri: str) -> Element:
        with self.__nest_link(iri) as _a:
            _a.text = ''.join(self.__iri_display_lines(iri))
        return _a

    @contextlib.contextmanager
    def __nest_card(self, tag: str) -> Generator[Element]:
        with (
            self._hue_turn_css() as _hue_turn_style,
            self.__hb.nest(
                tag,
                attrs={
                    'class': 'Browse__card',
                    'style': _hue_turn_style,
                },
            ) as _element,
        ):
            yield _element

    def __iri_thesaurus_labels(self, iri: str) -> list[str]:
        # TODO: consider requested language
        _labels: set[rdf.RdfObject] = set()
        _suffuniq = get_sufficiently_unique_iri(iri)
        _thesaurus_entry = combined_thesaurus__suffuniq().get(_suffuniq)
        if _thesaurus_entry:
            for _pred in _LINK_TEXT_PREDICATES:
                _labels.update(_thesaurus_entry.get(_pred, ()))
        _twoples = self.__current_data.tripledict.get(iri)
        if _twoples:
            for _pred in _LINK_TEXT_PREDICATES:
                _labels.update(_twoples.get(_pred, ()))
        return shuffled(_labels)

    @contextlib.contextmanager
    def _hue_turn_css(self) -> Generator[str]:
        _prior_turn = self.__last_hue_turn
        _hue_turn = (_prior_turn + _PHI) % 1.0
        self.__last_hue_turn = _hue_turn
        try:
            yield f'--hue-turn: {_hue_turn}turn;'
        finally:
            self.__last_hue_turn = _prior_turn

    def _queryparam_href(self, param_name: str, param_value: str | None) -> str:
        _base_url = self.response_focus.single_iri()
        if not is_local_url(_base_url):
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
        for _type_iri in self.__current_data.q(iri, RDF.type):
            self.__compact_link(_type_iri)
        _labels = self.__iri_thesaurus_labels(iri)
        if _labels:
            for _label in _labels:
                self.__literal(_label)

    def __iri_display_lines(self, iri: str) -> Generator[str]:
        _compact = self.iri_shorthand.compact_iri(iri)
        if _compact != iri:
            yield _compact
        else:
            (_scheme, _netloc, _path, _query, _fragment) = urlsplit(iri)
            # first line with path
            if is_local_url(iri):
                yield f'/{_path.lstrip('/')}'
            elif _netloc:
                yield f'://{_netloc}{_path}'
            else:
                yield f'{_scheme}:{_path}'
            # query and fragment separate
            if _query:
                yield from filter(bool, _QUERYPARAM_SPLIT_RE.split(f'?{_query}'))
            if _fragment:
                yield f'#{_fragment}'

    def __is_focus(self, iri: str) -> bool:
        return (iri in self.response_focus.iris)


def _append_class(el: Element, element_class: str) -> None:
    el.set(
        'class',
        ' '.join(filter(None, (element_class, el.get('class')))),
    )


def _is_sequence_obj(obj: rdf.RdfObject) -> bool:
    return (
        isinstance(obj, frozenset)
        and (RDF.type, RDF.Seq) in obj
    )


def _is_jsonapi_link_obj(obj: rdf.RdfObject) -> bool:
    return (
        isinstance(obj, frozenset)
        and (RDF.type, jsonapi.JSONAPI_LINK_OBJECT) in obj
    )


def _obj_ordering_key(obj: rdf.RdfObject) -> tuple[bool, ...]:
    return (
        not isinstance(obj, (rdf.Literal, *_PRIMITIVE_LITERAL_TYPES)),  # literal values first
        not isinstance(obj, str),  # iris next
        _is_jsonapi_link_obj(obj),  # jsonapi link objects last
    )
