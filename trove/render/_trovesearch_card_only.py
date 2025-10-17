from __future__ import annotations
import abc
from collections.abc import Generator, Iterator, Sequence
import json
import logging
from typing import Any, TYPE_CHECKING

from primitive_metadata import primitive_rdf as rdf

from trove import exceptions as trove_exceptions
from trove.vocab.jsonapi import JSONAPI_LINK_OBJECT
from trove.vocab.namespaces import TROVE, RDF
from ._base import BaseRenderer
if TYPE_CHECKING:
    from trove.util.json import JsonObject
    from trove.render.rendering import ProtoRendering

_logger = logging.getLogger(__name__)


class TrovesearchCardOnlyRenderer(BaseRenderer, abc.ABC):
    '''for search api responses that include only metadata about results

    very entangled with trove/trovesearch/trovesearch_gathering.py and trove/derive/osfmap_json.py
    '''
    PASSIVE_RENDER = False  # knows the properties it cares about
    INDEXCARD_DERIVER_IRI = TROVE['derive/osfmap_json']  # assumes osfmap_json
    _page_links: set[str]  # for use *after* iterating cards/card_pages
    __already_iterated_cards = False

    @abc.abstractmethod
    def multicard_rendering(self, card_pages: Iterator[Sequence[tuple[str, JsonObject]]]) -> ProtoRendering:
        raise NotImplementedError(f'{self.__class__.__name__} must implement `multicard_rendering`')

    def unicard_rendering(self, card_iri: str, osfmap_json: JsonObject) -> ProtoRendering:
        _page = [(card_iri, osfmap_json)]
        return self.multicard_rendering(card_pages=iter([_page]))

    def render_document(self) -> ProtoRendering:
        _focustypes = self.response_focus.type_iris
        if (TROVE.Cardsearch in _focustypes) or (TROVE.Valuesearch in _focustypes):
            return self.multicard_rendering(self._iter_card_pages())
        if TROVE.Indexcard in _focustypes:
            return self.unicard_rendering(
                self.response_focus.single_iri(),
                self._get_card_content(self.response_focus.single_iri()),
            )
        raise trove_exceptions.UnsupportedRdfType(_focustypes)

    def _iter_card_pages(self) -> Generator[list[tuple[str, JsonObject]]]:
        assert not self.__already_iterated_cards
        self.__already_iterated_cards = True
        self._page_links = set()
        for _page, _page_graph in self.response_gathering.ask_exhaustively(
            TROVE.searchResultPage, focus=self.response_focus
        ):
            if (RDF.type, JSONAPI_LINK_OBJECT) in _page:
                self._page_links.add(_page)
            elif rdf.is_container(_page):
                _cardpage: list[tuple[str, JsonObject]] = []
                for _search_result_blanknode in rdf.container_objects(_page):
                    try:
                        _card = next(
                            _obj
                            for _pred, _obj in _search_result_blanknode
                            if _pred == TROVE.indexCard
                        )
                    except StopIteration:
                        pass  # skip malformed
                    else:
                        _cardpage.append((
                            self._get_card_iri(_card),
                            self._get_card_content(_card, _page_graph),
                        ))
                yield _cardpage

    def _get_card_iri(self, card: str | rdf.RdfBlanknode) -> str:
        return card if isinstance(card, str) else ''

    def _get_card_content(
        self,
        card: str | rdf.RdfBlanknode,
        graph: rdf.RdfGraph | None = None,
    ) -> Any:
        if isinstance(card, str):
            _card_content = (
                next(self.response_gathering.ask(TROVE.resourceMetadata, focus=card))
                if graph is None
                else next(graph.q(card, TROVE.resourceMetadata), None)
            )
        elif isinstance(card, frozenset):
            _card_content = next(
                _obj
                for _pred, _obj in card
                if _pred == TROVE.resourceMetadata
            )
        else:
            raise trove_exceptions.ExpectedIriOrBlanknode(card)
        if isinstance(_card_content, rdf.QuotedGraph):
            return _card_content
        if isinstance(_card_content, rdf.Literal) and (RDF.JSON in _card_content.datatype_iris):
            return json.loads(_card_content.unicode_value)
        raise ValueError(card)
