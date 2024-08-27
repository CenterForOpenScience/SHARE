import contextlib
from unittest import mock

from share.search import index_strategy


@contextlib.contextmanager
def patch_index_strategies(strategies: dict[str, index_strategy.IndexStrategy]):
    index_strategy.all_index_strategies.cache_clear()
    with mock.patch.object(
        index_strategy,
        'all_index_strategies',
        return_value=strategies,
    ):
        breakpoint()
        yield
        breakpoint()
    index_strategy.all_index_strategies.cache_clear()
