from collections.abc import (
    Generator,
    Hashable,
    Iterable,
)


def iter_unique[T: Hashable](iterable: Iterable[T]) -> Generator[T]:
    '''
    >>> list(iter_unique([1,1,1]))
    [1]
    >>> list(iter_unique([1,2,3,2,4,2,1,5]))
    [1, 2, 3, 4, 5]
    '''
    _seen = set()
    for _item in iterable:
        if _item not in _seen:
            _seen.add(_item)
            yield _item
