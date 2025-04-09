from __future__ import annotations
import enum
from typing import Iterator

from django.conf import settings

from share.search.exceptions import IndexStrategyError
from share.models import FeatureFlag
from trove.trovesearch import search_params
from .sharev2_elastic8 import Sharev2Elastic8IndexStrategy
from .trovesearch_denorm import TrovesearchDenormIndexStrategy
from ._base import IndexStrategy
from ._indexnames import parse_indexname_parts


__all__ = (
    'IndexStrategy',
    'all_strategy_names',
    'each_strategy',
    'get_strategy',
    'get_strategy_for_sharev2_search',
    'get_strategy_for_trovesearch',
    'parse_specific_index_name',
    'parse_strategy_name',
)


class _AvailableStrategies(enum.Enum):
    '''static source of truth for available index strategies

    (don't import this enum directly -- access via the other functions in this module)
    '''
    if settings.ELASTICSEARCH8_URL:
        sharev2_elastic8 = Sharev2Elastic8IndexStrategy('sharev2_elastic8')
        trovesearch_denorm = TrovesearchDenormIndexStrategy('trovesearch_denorm')


if __debug__:
    for _strategy_enum in _AvailableStrategies:
        assert _strategy_enum.name == _strategy_enum.value.strategy_name, 'expected _AvailableStrategies enum name to match strategy name'


###
# module public interface

def all_strategy_names() -> frozenset[str]:
    return frozenset(_AvailableStrategies.__members__.keys())


def each_strategy() -> Iterator[IndexStrategy]:
    for _strat_enum in _AvailableStrategies:
        yield _strat_enum.value


def get_strategy(
    strategy_name: str,
    strategy_check: str = '',
    *,
    for_search: bool = False,
) -> IndexStrategy:
    try:
        _strategy: IndexStrategy = _AvailableStrategies[strategy_name].value
    except KeyError:
        raise IndexStrategyError(f'unrecognized strategy name "{strategy_name}"')
    if strategy_check:
        _strategy = _strategy.with_strategy_check(strategy_check)
    return (
        _strategy.pls_get_default_for_searching()
        if (for_search and not strategy_check)
        else _strategy
    )


def get_strategy_for_sharev2_search(requested_name: str | None = None) -> IndexStrategy:
    if requested_name:
        _name = requested_name
    elif settings.ELASTICSEARCH8_URL:
        _name = _AvailableStrategies.sharev2_elastic8.name
    else:
        raise IndexStrategyError('no available index for sharev2 search')
    return parse_strategy_name(_name)


def get_strategy_for_trovesearch(params: search_params.CardsearchParams) -> IndexStrategy:
    if params.index_strategy_name:  # specific strategy requested
        _strategy = parse_strategy_name(params.index_strategy_name, for_search=True)
    else:  # hard-coded default (...for now)
        _strategy = get_strategy(_AvailableStrategies.trovesearch_denorm.name, for_search=True)
    return _strategy


def parse_specific_index_name(index_name: str) -> IndexStrategy.SpecificIndex:
    try:
        _strategy = parse_strategy_name(index_name)
        return _strategy.parse_full_index_name(index_name)
    except IndexStrategyError:
        raise IndexStrategyError(f'invalid index_name "{index_name}"')


def parse_strategy_name(requested_strategy_name: str, *, for_search=False) -> IndexStrategy:
    (_strategyname, *_etc) = parse_indexname_parts(requested_strategy_name)
    return get_strategy(
        strategy_name=_strategyname,
        strategy_check=(_etc[0] if _etc else ''),
        for_search=for_search
    )
