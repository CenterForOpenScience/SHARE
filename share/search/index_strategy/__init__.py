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
from .trovesearch_denorm import TrovesearchDenormIndexStrategy
from ._base import IndexStrategy
from ._indexnames import parse_indexname_parts


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
    _all_strategies = {}
    for _strategy in _iter_all_index_strategies():
        if _strategy.name in _all_strategies:
            raise IndexStrategyError(f'strategy names must be unique! (duplicate "{_strategy.name}")')
        _all_strategies[_strategy.name] = _strategy
    return MappingProxyType(_all_strategies)  # a single cached readonly proxy -- set of strategy names immutable


def _iter_all_index_strategies():
    if settings.ELASTICSEARCH5_URL:
        yield Sharev2Elastic5IndexStrategy(name='sharev2_elastic5')
    if settings.ELASTICSEARCH8_URL:
        yield Sharev2Elastic8IndexStrategy(name='sharev2_elastic8')
        yield TroveIndexcardFlatsIndexStrategy(name='trove_indexcard_flats')
        yield TrovesearchDenormIndexStrategy(name='trovesearch_denorm')


def parse_strategy_request(requested_strategy_name: str) -> IndexStrategy:
    (_strategyname, *_etc) = parse_indexname_parts(requested_strategy_name)
    try:
        _strategy = get_index_strategy(
            _strategyname,
            subname=(_etc[0] if _etc else ''),
        )
    except IndexStrategyError:
        raise IndexStrategyError(f'unrecognized strategy name "{requested_strategy_name}"')
    else:
        return _strategy


def parse_index_name(index_name: str) -> IndexStrategy.SpecificIndex:
    try:
        (_strategy_name, _strategy_check, *_etc) = parse_indexname_parts(index_name)
        _strategy = get_index_strategy(_strategy_name, _strategy_check)
        return _strategy.get_index_by_subname(*_etc)
    except IndexStrategyError:
        raise IndexStrategyError(f'invalid index_name "{index_name}"')


def get_index_strategy(strategy_name: str, subname: str = '') -> IndexStrategy:
    try:
        return all_index_strategies()[strategy_name]
    except KeyError:
        raise IndexStrategyError(f'unknown index strategy "{strategy_name}"')


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
                return _index_strategy.get_index_by_subname(indexname_or_strategyname)
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
    elif FeatureFlag.objects.flag_is_up(FeatureFlag.TROVESEARCH_DENORMILY):
        _name = 'trovesearch_denorm'
    else:
        _name = 'trove_indexcard_flats'
    return get_specific_index(_name, for_search=True)
