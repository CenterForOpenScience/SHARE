import contextlib
import enum
from typing import Iterable
from unittest import mock

from share.search import index_strategy


@contextlib.contextmanager
def patch_index_strategies(strategies: Iterable[index_strategy.IndexStrategy]):
    with mock.patch.object(index_strategy, '_AvailableStrategies', new=enum.Enum(
        '_AvailableStrategies', [
            (_strategy.strategy_name, _strategy)
            for _strategy in strategies
        ],
    )):
        yield
