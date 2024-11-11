import json
from typing import Iterable

from primitive_metadata import primitive_rdf as rdf

from trove import exceptions as trove_exceptions
from trove.vocab.namespaces import TROVE, RDF
from ._base import BaseRenderer


class BaseSimpleOsfmapRenderer(BaseRenderer):
    '''for "simple" search api responses based on osfmap json

    (very entangled with trove/trovesearch/trovesearch_gathering.py)
    '''

    def render_unicard_document(self, card_iri: str, osfmap_json: dict) -> str | None:
        raise NotImplementedError

    def render_multicard_document(self, cards: Iterable[tuple[str, dict]]) -> str | None:
        raise NotImplementedError

    def render_document(self) -> str | None:
        _focustypes = set(self.response_data.q(self.response_focus_iri, RDF.type))
        if (TROVE.Cardsearch in _focustypes) or (TROVE.Valuesearch in _focustypes):
            return self.render_multicard_document(self._iter_search_contents())
        if TROVE.Indexcard in _focustypes:
            return self.render_unicard_document(
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
                _card = next(
                    _obj
                    for _pred, _obj in _search_result
                    if _pred == TROVE.indexCard
                )
                yield self._get_card_content(_card)

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
        assert isinstance(_card_content, rdf.Literal)
        assert RDF.JSON in _card_content.datatype_iris
        return json.loads(_card_content.unicode_value)
