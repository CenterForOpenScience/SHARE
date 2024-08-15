import contextlib
import typing
from unittest import mock

if typing.TYPE_CHECKING:
    from share.search import index_strategy


def patch_feature_flag(*flag_names, up=True):
    from share.models.feature_flag import FeatureFlag
    _old_isup = FeatureFlag.objects.flag_is_up

    def _patched_isup(flag_name):
        if flag_name in flag_names:
            return up
        return _old_isup(flag_name)
    return mock.patch.object(FeatureFlag.objects, 'flag_is_up', new=_patched_isup)


@contextlib.contextmanager
def patch_index_strategies(strategies: dict[str, index_strategy.IndexStrategy]):
    index_strategy.all_index_strategies.cache_clear()
    with mock.patch(
        'share.bin.search.index_strategy._iter_all_index_strategies',
        return_value=strategies.items(),
    ):
        yield
    index_strategy.all_index_strategies.cache_clear()
