import contextlib
from typing import Iterable
from unittest import mock

from share.search import index_strategy


@contextlib.contextmanager
def patch_index_strategies(strategies: Iterable[index_strategy.IndexStrategy]):
    index_strategy.all_strategy_names.cache_clear()
    with mock.patch.object(
        index_strategy,
        'each_strategy',
        return_value=strategies,
    ):
        yield
    index_strategy.all_strategy_names.cache_clear()
