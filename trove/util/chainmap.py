from collections.abc import Sequence, Mapping, Iterator
import dataclasses
from typing import Self


@dataclasses.dataclass
class SimpleChainMap[K, V](Mapping[K, V]):
    """Combine multiple mappings for sequential lookup.

    (inspired by rejecting the suggested "greatly simplified read-only version of Chainmap"
    linked from python docs: https://code.activestate.com/recipes/305268/ )

    >>> _map = SimpleChainMap([{'a':1, 'b':2}, {'a':3, 'd':4}])
    >>> _map['a']
    1
    >>> _map['d']
    4
    >>> _map['f']
    Traceback (most recent call last):
      ...
    KeyError: 'f'
    >>> 'b' in _map
    True
    >>> 'c' in _map
    False
    >>> 'd' in _map
    True
    >>> _map.get('a', 10)
    1
    >>> _map.get('b', 20)
    2
    >>> _map.get('d', 30)
    4
    >>> _map.get('f', 40)
    40
    >>> sorted(_map)
    ['a', 'b', 'd']
    >>> _map
    SimpleChainMap(maps=[{'a': 1, 'b': 2}, {'a': 3, 'd': 4}])
    >>> _map.with_new({'a': 11, 'z': 13})
    SimpleChainMap(maps=[{'a': 11, 'z': 13}, {'a': 1, 'b': 2}, {'a': 3, 'd': 4}])
    >>> _map.with_new({'a': 17}).get('a')
    17
    """
    maps: Sequence[Mapping[K, V]]

    def __getitem__(self, key: K) -> V:
        for _mapping in self.maps:
            try:
                return _mapping[key]
            except KeyError:
                pass
        raise KeyError(key)

    def __iter__(self) -> Iterator[K]:
        _seen: set = set()
        for _mapping in self.maps:
            for _key in _mapping.keys():
                if _key not in _seen:
                    yield _key
                    _seen.add(_key)

    def __len__(self) -> int:  # for Mapping
        return sum(1 for _ in self)  # use __iter__

    def with_new(self, new_map: Mapping[K, V]) -> Self:
        return dataclasses.replace(self, maps=[new_map, *self.maps])
