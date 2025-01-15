from __future__ import annotations
import enum
import functools
from types import MappingProxyType
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


class _StrategyTypes(enum.Enum):
    if settings.ELASTICSEARCH5_URL:
        sharev2_elastic5 = Sharev2Elastic5IndexStrategy
    if settings.ELASTICSEARCH8_URL:
        sharev2_elastic8 = Sharev2Elastic8IndexStrategy
        trove_indexcard_flats = TroveIndexcardFlatsIndexStrategy
        trovesearch_denorm = TrovesearchDenormIndexStrategy

    def new_strategy_instance(self, strategy_check: str = '', *, for_search=False) -> IndexStrategy:
        _strategy_type = self.value
        _strategy = _strategy_type(strategy_name=self.name, strategy_check=strategy_check)
        return (
            _strategy.get_default_search_strategy()
            if (for_search and not strategy_check)
            else _strategy
        )


def each_strategy() -> Iterator[IndexStrategy]:
    for _strat_enum in _StrategyTypes:
        yield _strat_enum.new_strategy_instance()


def all_strategy_names() -> frozenset[str]:
    return frozenset(_StrategyTypes.__members__.keys())


def parse_strategy_name(requested_strategy_name: str, *, for_search=False) -> IndexStrategy:
    (_strategyname, *_etc) = parse_indexname_parts(requested_strategy_name)
    return get_strategy(
        strategy_name=_strategyname,
        strategy_check=(_etc[0] if _etc else ''),
        for_search=for_search
    )


def parse_specific_index_name(index_name: str) -> IndexStrategy.SpecificIndex:
    try:
        _strategy = parse_strategy_name(index_name)
        return _strategy.parse_full_index_name(index_name)
    except IndexStrategyError:
        raise IndexStrategyError(f'invalid index_name "{index_name}"')


def get_strategy(
    strategy_name: str,
    strategy_check: str = '',
    *,
    for_search: bool = False,
) -> IndexStrategy:
    try:
        _strat_enum = _StrategyTypes[strategy_name]
    except KeyError:
        raise IndexStrategyError(f'unrecognized strategy name "{strategy_name}"')
    return _strat_enum.new_strategy_instance(strategy_check=strategy_check)



def get_strategy_for_sharev2_search(requested_name=None) -> IndexStrategy.SpecificIndex:
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


def get_strategy_for_trovesearch(params: search_params.CardsearchParams) -> IndexStrategy.SpecificIndex:
    if params.index_strategy_name:  # specific strategy requested
        _strategy = parse_strategy_name(params.index_strategy_name, for_search=True)
    else:
        _default_strategy_enum = (
            _StrategyTypes.trovesearch_denorm
            if FeatureFlag.objects.flag_is_up(FeatureFlag.TROVESEARCH_DENORMILY)
            else _StrategyTypes.trove_indexcard_flats
        )
        _strategy = _default_strategy_enum.new_strategy_instance()
