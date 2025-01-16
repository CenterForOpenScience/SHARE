from __future__ import annotations
import enum
from typing import Iterator

from django.conf import settings

from share.search.exceptions import IndexStrategyError
from share.models import FeatureFlag
from trove.trovesearch import search_params
from .sharev2_elastic5 import Sharev2Elastic5IndexStrategy
from .sharev2_elastic8 import Sharev2Elastic8IndexStrategy
from .trove_indexcard_flats import TroveIndexcardFlatsIndexStrategy
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

    if settings.ELASTICSEARCH5_URL:
        sharev2_elastic5 = Sharev2Elastic5IndexStrategy('sharev2_elastic5')

    if settings.ELASTICSEARCH8_URL:
        sharev2_elastic8 = Sharev2Elastic8IndexStrategy('sharev2_elastic8')
        trove_indexcard_flats = TroveIndexcardFlatsIndexStrategy('trove_indexcard_flats')
        trovesearch_denorm = TrovesearchDenormIndexStrategy('trovesearch_denorm')


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
    elif (
        settings.ELASTICSEARCH5_URL
        and not FeatureFlag.objects.flag_is_up(FeatureFlag.ELASTIC_EIGHT_DEFAULT)
    ):
        _name = 'sharev2_elastic5'
    elif settings.ELASTICSEARCH8_URL:
        _name = 'sharev2_elastic8'
    else:
        raise IndexStrategyError('no available index for sharev2 search')
    return parse_strategy_name(_name)


def get_strategy_for_trovesearch(params: search_params.CardsearchParams) -> IndexStrategy:
    if params.index_strategy_name:  # specific strategy requested
        _strategy = parse_strategy_name(params.index_strategy_name, for_search=True)
    else:
        _strategy = get_strategy(
            strategy_name=(
                _AvailableStrategies.trovesearch_denorm.name
                if FeatureFlag.objects.flag_is_up(FeatureFlag.TROVESEARCH_DENORMILY)
                else _AvailableStrategies.trove_indexcard_flats.name
            ),
            for_search=True,
        )
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
