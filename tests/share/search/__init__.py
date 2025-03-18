import contextlib
import enum
from typing import Iterable
from unittest import mock


@contextlib.contextmanager
def patch_index_strategies(strategies: Iterable):
    from share.search import index_strategy
    with mock.patch.object(index_strategy, '_AvailableStrategies', new=enum.Enum(
        '_AvailableStrategies', [
            (_strategy.strategy_name, _strategy)
            for _strategy in strategies
        ],
    )):
        yield


@contextlib.contextmanager
def patch_index_strategy(strategy):
    from share.search import index_strategy as _module_to_patch
    with (
        mock.patch.object(_module_to_patch, 'all_strategy_names', return_value=frozenset([strategy.strategy_name])),
        mock.patch.object(_module_to_patch, 'each_strategy', return_value=[strategy]),
        mock.patch.object(_module_to_patch, 'get_strategy', return_value=strategy),
    ):
        yield
