import random
import typing


_T = typing.TypeVar('_T')


def shuffled(items: typing.Iterable[_T]) -> list[_T]:
    _itemlist = list(items)
    random.shuffle(_itemlist)
    return _itemlist
