import urllib

from primitive_metadata import primitive_rdf as rdf

from trove import exceptions as trove_exceptions


###
# type aliases
Propertypath = tuple[str, ...]
PropertypathSet = frozenset[Propertypath]

###
# constants

# between each step in a property path "foo.bar.baz"
PROPERTYPATH_DELIMITER = '.'

# special path-step that matches any property
GLOB_PATHSTEP = '*'
ONE_GLOB_PROPERTYPATH: Propertypath = (GLOB_PATHSTEP,)


def is_globpath(path: Propertypath) -> bool:
    '''
    >>> is_globpath(('*',))
    True
    >>> is_globpath(('*', '*'))
    True
    >>> is_globpath(('*', 'url:url'))
    False
    >>> is_globpath(())
    False
    '''
    return all(_pathstep == GLOB_PATHSTEP for _pathstep in path)


def make_globpath(length: int) -> Propertypath:
    '''
    >>> make_globpath(1)
    ('*',)
    >>> make_globpath(2)
    ('*', '*')
    >>> make_globpath(5)
    ('*', '*', '*', '*', '*')
    '''
    return ONE_GLOB_PROPERTYPATH * length


def parse_propertypath(
    serialized_path: str,
    shorthand: rdf.IriShorthand,
    allow_globs: bool = False,
) -> Propertypath:
    _path = tuple(
        shorthand.expand_iri(_pathstep)
        for _pathstep in serialized_path.split(PROPERTYPATH_DELIMITER)
    )
    if GLOB_PATHSTEP in _path:
        if not allow_globs:
            raise trove_exceptions.InvalidPropertyPath(serialized_path, 'no * allowed')
        if any(_pathstep != GLOB_PATHSTEP for _pathstep in _path):
            raise trove_exceptions.InvalidPropertyPath(
                serialized_path,
                f'path must be all * or no * (got {serialized_path})',
            )
    return _path


def propertypathstep_key(
    pathstep: str,
    shorthand: rdf.IriShorthand,
) -> str:
    if pathstep == GLOB_PATHSTEP:
        return pathstep
    # assume iri
    return urllib.parse.quote(shorthand.compact_iri(pathstep))


def propertypath_key(
    path: Propertypath,
    shorthand: rdf.IriShorthand,
) -> str:
    return PROPERTYPATH_DELIMITER.join(
        propertypathstep_key(_pathstep, shorthand)
        for _pathstep in path
    )
