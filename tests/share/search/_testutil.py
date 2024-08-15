import contextlib
import typing
from unittest import mock

if typing.TYPE_CHECKING:
    from share.search import index_strategy


@contextlib.contextmanager
def patch_index_strategies(strategies: dict[str, index_strategy.IndexStrategy]):
    index_strategy.all_index_strategies.cache_clear()
    with mock.patch(
        'share.bin.search.index_strategy._iter_all_index_strategies',
        return_value=strategies.items(),
    ):
        yield
    index_strategy.all_index_strategies.cache_clear()
