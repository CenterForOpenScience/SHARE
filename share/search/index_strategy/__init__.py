from __future__ import annotations
import functools
from types import MappingProxyType

from django.conf import settings

from share.search.exceptions import IndexStrategyError
from share.models import FeatureFlag
from trove.trovesearch import search_params
from .sharev2_elastic5 import Sharev2Elastic5IndexStrategy
from .sharev2_elastic8 import Sharev2Elastic8IndexStrategy
from .trove_indexcard_flats import TroveIndexcardFlatsIndexStrategy
from ._base import IndexStrategy


__all__ = (
    'IndexStrategy',
    'all_index_strategies',
    'get_index_for_sharev2_search',
    'get_index_for_trovesearch',
    'get_index_strategy',
    'get_specific_index',
)


@functools.cache
def all_index_strategies() -> MappingProxyType[str, IndexStrategy]:
    return MappingProxyType({
        _strategy.name: _strategy
        for _strategy in _iter_all_index_strategies()
    })


def _iter_all_index_strategies():
    if settings.ELASTICSEARCH5_URL:
        yield Sharev2Elastic5IndexStrategy(name='sharev2_elastic5')
    if settings.ELASTICSEARCH8_URL:
        yield Sharev2Elastic8IndexStrategy(name='sharev2_elastic8')
        yield TroveIndexcardFlatsIndexStrategy(name='trove_indexcard_flats')


def get_index_strategy(strategyname: str) -> IndexStrategy:
    try:
        return all_index_strategies()[strategyname]
    except KeyError:
        raise IndexStrategyError(f'unknown index strategy "{strategyname}"')


def get_specific_index(indexname_or_strategyname: str, *, for_search=False) -> IndexStrategy.SpecificIndex:
    try:
        _strategy = get_index_strategy(indexname_or_strategyname)
        return (
            _strategy.pls_get_default_for_searching()
            if for_search
            else _strategy.for_current_index()
        )
    except IndexStrategyError:
        for _index_strategy in all_index_strategies().values():
            try:
                return _index_strategy.for_specific_index(indexname_or_strategyname)
            except IndexStrategyError:
                pass
    raise IndexStrategyError(f'unrecognized name "{indexname_or_strategyname}"')


def get_index_for_sharev2_search(requested_name=None) -> IndexStrategy.SpecificIndex:
    if requested_name:
        _name = requested_name
    elif (
        settings.ELASTICSEARCH5_URL
        and not FeatureFlag.objects.flag_is_up(FeatureFlag.ELASTIC_EIGHT_DEFAULT)
    ):
        _name = 'sharev2_elastic5'
    elif settings.ELASTICSEARCH8_URL:
        _name = 'sharev2_elastic8'
    else:
        raise IndexStrategyError('no available index for sharev2 search')
    return get_specific_index(_name, for_search=True)


def get_index_for_trovesearch(params: search_params.CardsearchParams) -> IndexStrategy.SpecificIndex:
    if params.index_strategy_name:  # specific strategy requested
        _name = params.index_strategy_name
    else:
        _name = 'trove_indexcard_flats'
    return get_specific_index(_name, for_search=True)
