import functools
import importlib.metadata


__all__ = ('get_shtrove_version',)


@functools.cache
def get_shtrove_version() -> str:
    return importlib.metadata.version('shtrove')
