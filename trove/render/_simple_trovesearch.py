import json
from typing import Iterable

from primitive_metadata import primitive_rdf as rdf

from trove import exceptions as trove_exceptions
from trove.vocab.namespaces import TROVE, RDF
from ._base import BaseRenderer
from ._rendering import ProtoRendering, SimpleRendering


class SimpleTrovesearchRenderer(BaseRenderer):
    '''for "simple" search api responses (including only result metadata)

    (very entangled with trove/trovesearch/trovesearch_gathering.py)
    '''

    def simple_unicard_rendering(self, card_iri: str, osfmap_json: dict) -> str:
        raise NotImplementedError

    def simple_multicard_rendering(self, cards: Iterable[tuple[str, dict]]) -> str:
        raise NotImplementedError

    def unicard_rendering(self, card_iri: str, osfmap_json: dict) -> ProtoRendering:
        return SimpleRendering(
            mediatype=self.MEDIATYPE,
            rendered_content=self.simple_unicard_rendering(card_iri, osfmap_json),
        )

    def multicard_rendering(self, cards: Iterable[tuple[str, dict]]) -> ProtoRendering:
        return SimpleRendering(
            mediatype=self.MEDIATYPE,
            rendered_content=self.simple_multicard_rendering(cards),
        )

    def render_document(self) -> ProtoRendering:
        _focustypes = set(self.response_data.q(self.response_focus_iri, RDF.type))
        if (TROVE.Cardsearch in _focustypes) or (TROVE.Valuesearch in _focustypes):
            return self.multicard_rendering(self._iter_search_contents())
        if TROVE.Indexcard in _focustypes:
            return self.unicard_rendering(
                self.response_focus_iri,
                self._get_card_content(self.response_focus_iri),
            )
        raise trove_exceptions.UnsupportedRdfType(_focustypes)

    def _iter_search_contents(self):
        # just each card's contents
        for _page in self.response_data.q(self.response_focus_iri, TROVE.searchResultPage):
            if not rdf.is_container(_page):
                continue  # filter out page links
            for _search_result in rdf.sequence_objects_in_order(_page):
                try:
                    _card = next(
                        _obj
                        for _pred, _obj in _search_result
                        if _pred == TROVE.indexCard
                    )
                except StopIteration:
                    continue  # skip malformed
                yield self._get_card_iri(_card), self._get_card_content(_card)

    def _get_card_iri(self, card: str | rdf.RdfBlanknode) -> str:
        return card if isinstance(card, str) else ''

    def _get_card_content(self, card: str | rdf.RdfBlanknode) -> dict:
        if isinstance(card, str):
            _card_content = next(self.response_data.q(card, TROVE.resourceMetadata))
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
