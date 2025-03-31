import abc
from collections.abc import Callable
import logging

from primitive_metadata import gather

from share.search import index_strategy
from trove.trovesearch.search_handle import BasicSearchHandle
from trove.trovesearch.search_params import (
    CardsearchParams,
    ValuesearchParams,
)
from trove.trovesearch.trovesearch_gathering import (
    trovesearch_by_indexstrategy,
    CardsearchFocus,
    ValuesearchFocus,
)
from trove.util.trove_params import BasicTroveParams
from ._base import BaseTroveView


logger = logging.getLogger(__name__)


_TrovesearchHandler = Callable[[BasicTroveParams], BasicSearchHandle]


class _BaseTrovesearchView(BaseTroveView, abc.ABC):
    focus_type: type[gather.Focus] = gather.Focus  # expected on subclasses

    gathering_organizer = trovesearch_by_indexstrategy  # for BaseTroveView

    def _build_focus(self, url, params):  # override BaseTroveView
        _strategy = index_strategy.get_strategy_for_trovesearch(params)
        return self.focus_type.new(
            iris=url,
            search_params=params,
            search_handle=self.get_search_handle(_strategy, params),
        )

    def get_search_handle(self, strategy, search_params) -> BasicSearchHandle:
        return self._get_wrapped_handler(strategy)(search_params)

    def get_search_handler(
        self,
        strategy: index_strategy.IndexStrategy,
    ) -> _TrovesearchHandler:
        raise NotImplementedError

    def _get_wrapped_handler(self, strategy: index_strategy.IndexStrategy):
        _raw_handler = self.get_search_handler(strategy)

        def _wrapped_handler(search_params):
            _handle = _raw_handler(search_params)
            _handle.handler = _wrapped_handler
            return _handle
        return _wrapped_handler


class CardsearchView(_BaseTrovesearchView):
    focus_type = CardsearchFocus
    params_type = CardsearchParams

    def get_search_handler(self, strategy):
        return strategy.pls_handle_cardsearch


class ValuesearchView(_BaseTrovesearchView):
    focus_type = ValuesearchFocus
    params_type = ValuesearchParams

    def get_search_handler(self, strategy):
        return strategy.pls_handle_valuesearch
