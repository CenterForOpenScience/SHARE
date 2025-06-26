from collections.abc import Mapping
import types
from typing import Any

_FROZEN_TYPES = (
    tuple,
    frozenset,
    str,
    int,
    float,
)


def freeze(obj: Any) -> Any:
    '''
    >>> freeze([1, 1, 2])
    (1, 1, 2)
    >>> freeze({3})
    frozenset({3})
    >>> freeze('five')
    'five'
    >>> freeze({8: [13, 21, {34}]})
    mappingproxy({8: (13, 21, frozenset({34}))})
    >>> freeze(object())
    Traceback (most recent call last):
      ...
    ValueError: how freeze <object object at 0x...>?
    '''
    if isinstance(obj, set):
        return frozenset(obj)  # use hashability to approximate immutability
    if isinstance(obj, (list, tuple)):
        return tuple(map(freeze, obj))
    if isinstance(obj, dict):
        return freeze_mapping(obj)
    if isinstance(obj, _FROZEN_TYPES):
        return obj
    raise ValueError(f'how freeze {obj!r}?')


def freeze_mapping[K, V](_map: Mapping[K, V]) -> Mapping[K, V]:
    _mutable_mapping: dict[K, V] = {}
    for _key, _val in _map.items():
        _mutable_mapping[_key] = freeze(_val)
    return types.MappingProxyType(_mutable_mapping)
