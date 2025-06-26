from collections.abc import Iterable
import random


def shuffled[T](items: Iterable[T]) -> list[T]:
    _itemlist = list(items)
    random.shuffle(_itemlist)
    return _itemlist
