import json
from typing import Iterator, Any

from primitive_metadata import primitive_rdf as rdf

from trove import exceptions as trove_exceptions
from trove.vocab.jsonapi import JSONAPI_LINK_OBJECT
from trove.vocab.namespaces import TROVE, RDF
from ._base import BaseRenderer
from ._rendering import ProtoRendering, SimpleRendering


class SimpleTrovesearchRenderer(BaseRenderer):
    '''for "simple" search api responses (including only result metadata)

    (very entangled with trove/trovesearch/trovesearch_gathering.py)
    '''
    PASSIVE_RENDER = False  # knows the properties it cares about
    _page_links: set
    __already_iterated_cards = False

    def simple_unicard_rendering(self, card_iri: str, osfmap_json: dict) -> str:
        raise NotImplementedError

    def simple_multicard_rendering(self, cards: Iterator[tuple[str, dict]]) -> str:
        raise NotImplementedError

    def unicard_rendering(self, card_iri: str, osfmap_json: dict) -> ProtoRendering:
        return SimpleRendering(  # type: ignore[return-value]
            mediatype=self.MEDIATYPE,
            rendered_content=self.simple_unicard_rendering(card_iri, osfmap_json),
        )

    def multicard_rendering(self, card_pages: Iterator[dict[str, dict]]) -> ProtoRendering:
        _cards = (
            (_card_iri, _card_contents)
            for _page in card_pages
            for _card_iri, _card_contents in _page.items()
        )
        return SimpleRendering(  # type: ignore[return-value]
            mediatype=self.MEDIATYPE,
            rendered_content=self.simple_multicard_rendering(_cards),
        )

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

    def _iter_card_pages(self) -> Iterator[dict[str, Any]]:
        assert not self.__already_iterated_cards
        self.__already_iterated_cards = True
        self._page_links = set()
        for _page, _page_graph in self.response_gathering.ask_exhaustively(
            TROVE.searchResultPage, focus=self.response_focus
        ):
            if (RDF.type, JSONAPI_LINK_OBJECT) in _page:
                self._page_links.add(_page)
            elif rdf.is_container(_page):
                _cardpage = []
                for _search_result in rdf.container_objects(_page):
                    try:
                        _card = next(
                            _obj
                            for _pred, _obj in _search_result
                            if _pred == TROVE.indexCard
                        )
                    except StopIteration:
                        pass  # skip malformed
                    else:
                        _cardpage.append(_card)
                yield {
                    self._get_card_iri(_card): self._get_card_content(_card, _page_graph)
                    for _card in _cardpage
                }

    def _get_card_iri(self, card: str | rdf.RdfBlanknode) -> str:
        return card if isinstance(card, str) else ''

    def _get_card_content(
        self,
        card: str | rdf.RdfBlanknode,
        graph: rdf.RdfGraph | None = None,
    ) -> dict:
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
