from __future__ import annotations
import functools
from types import MappingProxyType
import typing

from django.conf import settings

from share.search.exceptions import IndexStrategyError
from share.models import FeatureFlag

if typing.TYPE_CHECKING:
    from ._base import IndexStrategy


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
        yield TroveIndexcardFlatteryIndexStrategy(name='trove_indexcard_flattery')


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


def get_for_trovesearch(search_params: CardsearchParams) -> 'IndexStrategy.SpecificIndex':
    if search_params.index_strategy_name:  # specific strategy requested
        _name = search_params.index_strategy_name
    else:
        _name = (
            'trove_indexcard_flattery'
            if FeatureFlag.objects.flag_is_up(FeatureFlag.USE_FLATTERY_STRATEGY)
            else 'trove_indexcard_flats'
        )
    try:  # could be a strategy name
        return cls.get_by_name(_name).pls_get_default_for_searching()
    except IndexStrategyError:
        try:  # could be a specific indexname
            return cls.get_specific_index(_name)
        except IndexStrategyError:
            raise IndexStrategyError(f'unknown name: "{_name}"')

def _load_from_settings(index_strategy_name, index_strategy_settings):
    assert set(index_strategy_settings) == {'INDEX_STRATEGY_CLASS', 'CLUSTER_SETTINGS'}, (
        'values in settings.ELASTICSEARCH[\'INDEX_STRATEGIES\'] must have keys: '
        'INDEX_STRATEGY_CLASS, CLUSTER_SETTINGS'
    )
    class_path = index_strategy_settings['INDEX_STRATEGY_CLASS']
    module_name, separator, class_name = class_path.rpartition('.')
    if not separator:
        raise IndexStrategyError(f'INDEX_STRATEGY_CLASS should be importable dotted-path to an IndexStrategy class; got "{class_path}"')
    assert module_name.startswith('share.search.index_strategy.'), (
        'for now, INDEX_STRATEGY_CLASS must start with "share.search.index_strategy."'
        f' (got "{module_name}")'
    )
    index_strategy_class = getattr(importlib.import_module(module_name), class_name)
    assert issubclass(index_strategy_class, cls)
    return index_strategy_class(
        name=index_strategy_name,
        cluster_settings=index_strategy_settings['CLUSTER_SETTINGS'],
    )

