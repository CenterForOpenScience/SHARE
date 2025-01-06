import collections.abc
import types


_FROZEN_TYPES = (
    tuple,
    frozenset,
    types.MappingProxyType,
    str,
    int,
    float,
)


def freeze(obj):
    if isinstance(obj, dict):
        return freeze_mapping(obj)
    if isinstance(obj, set):
        return frozenset(obj)
    if isinstance(obj, list):
        return tuple(obj)
    if isinstance(obj, _FROZEN_TYPES):
        return obj
    raise ValueError(f'how freeze {obj!r}?')


def freeze_mapping(_base_mapping=None, /, **kwargs) -> collections.abc.Mapping:
    _mutable_mapping = {}
    for _map in (_base_mapping, kwargs):
        if _map is not None:
            for _key, _val in _map.items():
                _mutable_mapping[_key] = freeze(_val)
    return types.MappingProxyType(_mutable_mapping)
