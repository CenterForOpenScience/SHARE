from typing import Iterable

from primitive_metadata import primitive_rdf as rdf

from trove import exceptions as trove_exceptions
from trove.vocab.namespaces import TROVE, RDF
from ._base import BaseRenderer


class BaseSimpleCardRenderer(BaseRenderer):
    '''for "simple" search api responses -- very entangled with trove/trovesearch/trovesearch_gathering.py
    '''
    def render_unicard_document(self, card_iri, card_content) -> str | None:
        raise NotImplementedError

    def render_multicard_document(self, cards_iris_and_contents: Iterable[tuple]) -> str | None:
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

    def _get_card_content(self, card: str | rdf.Blanknode):
        if isinstance(card, str):
            return next(self.response_data.q(card, TROVE.resourceMetadata))
        if isinstance(card, frozenset):
            return next(
                _obj
                for _pred, _obj in card
                if _pred == TROVE.resourceMetadata
            )
        raise trove_exceptions.ExpectedIriOrBlanknode(card)
