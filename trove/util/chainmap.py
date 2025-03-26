from collections.abc import Sequence, Mapping
import dataclasses


@dataclasses.dataclass
class SimpleChainMap(Mapping):
    """Combine multiple mappings for sequential lookup.

    For example, to emulate Python's normal lookup sequence:

        import __builtin__
        pylookup = SimpleChainMap([locals(), globals(), vars(__builtin__)])

    >>> _map = SimpleChainMap([{'a':1, 'b':2}, {'a':3, 'd':4}])
    >>> _map['a']
    1
    >>> _map['d']
    4
    >>> _map['f']
    KeyError
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
    """
    maps: Sequence[Mapping]

    def __getitem__(self, key):
        for _mapping in self.maps:
            try:
                return _mapping[key]
            except KeyError:
                pass
        raise KeyError(key)

    def __iter__(self):
        _seen: set = set()
        for _mapping in self.maps:
            yield from set(_mapping.keys()).difference(_seen)
            _seen.update(_mapping.keys())

    def __len__(self):
        return len(self.keys())

    def with_new(self, new_map):
        return dataclasses.replace(self, maps=[new_map, *self.maps])
