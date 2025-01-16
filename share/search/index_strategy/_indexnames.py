from share.search.exceptions import IndexStrategyError


INDEXNAME_DELIM = '__'  # used to separate indexnames into a list of meaningful values


def is_valid_indexname_part(indexname_part: str) -> bool:
    return bool(INDEXNAME_DELIM not in indexname_part)


def raise_if_invalid_indexname_part(indexname_part: str) -> None:
    if INDEXNAME_DELIM in indexname_part:
        raise IndexStrategyError(f'name may not contain "{INDEXNAME_DELIM}" (got "{indexname_part}")')


def combine_indexname_parts(*indexname_parts: str) -> str:
    return INDEXNAME_DELIM.join(filter(bool, indexname_parts))


def parse_indexname_parts(name: str) -> list[str]:
    return name.split(INDEXNAME_DELIM)
