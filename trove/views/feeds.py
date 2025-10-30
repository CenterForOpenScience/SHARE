from __future__ import annotations
import dataclasses
from typing import TYPE_CHECKING

from trove.render.cardsearch_rss import CardsearchRssRenderer
from trove.render.cardsearch_atom import CardsearchAtomRenderer
from trove.trovesearch.search_params import (
    CardsearchParams,
    SortParam,
    ValueType,
)
from trove.views.search import CardsearchView
from trove.vocab.namespaces import DCTERMS

if TYPE_CHECKING:
    from django.http import HttpRequest


class CardsearchRssView(CardsearchView):
    def _get_renderer_type(self, request: HttpRequest):
        '''override method from BaseTroveView

        ignore requested mediatype; always render RSS
        '''
        return CardsearchRssRenderer

    def _parse_params(self, request: HttpRequest):
        '''override method from BaseTroveView

        ignore requested sort; always sort by date created, descending
        '''
        _params: CardsearchParams = super()._parse_params(request)
        return dataclasses.replace(_params, sort_list=(
            SortParam(
                value_type=ValueType.DATE,
                propertypath=(DCTERMS.created,),
                descending=True,
            ),
        ))


class CardsearchAtomView(CardsearchRssView):
    def _get_renderer_type(self, request: HttpRequest):
        '''override method from BaseTroveView

        ignore requested mediatype; always render Atom
        '''
        return CardsearchAtomRenderer
