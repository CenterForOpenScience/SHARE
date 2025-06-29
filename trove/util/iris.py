import json
import re
import urllib.parse as _urp

from trove import exceptions as trove_exceptions


# quoth <https://www.rfc-editor.org/rfc/rfc3987.html#section-2.2>:
#   scheme = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )
IRI_SCHEME_REGEX = re.compile(
    r'[a-z]'            # one letter from the english alphabet
    r'[a-z0-9+-.]*'     # zero or more letters, decimal numerals, or the symbols `+`, `-`, or `.`
)
IRI_SCHEME_REGEX_IGNORECASE = re.compile(IRI_SCHEME_REGEX.pattern, flags=re.IGNORECASE)
COLON = ':'
COLON_SLASH_SLASH = '://'
QUOTED_IRI_REGEX = re.compile(
    f'{IRI_SCHEME_REGEX.pattern}{re.escape(_urp.quote(COLON))}'
    f'|{re.escape(_urp.quote(COLON_SLASH_SLASH))}'
)
UNQUOTED_IRI_REGEX = re.compile(f'{IRI_SCHEME_REGEX.pattern}{COLON}|{COLON_SLASH_SLASH}')

# treat similar-enough IRIs as equivalent, based on a wild assertion:
#   if two IRIs differ only in their `scheme`
#   and have non-empty `authority` component,
#   they may safely be considered equivalent.
# (while this is not strictly true, it should be true enough and helps avoid
# hand-wringing about "http" vs "https" -- use either or both, it's fine)


def get_sufficiently_unique_iri(iri: str) -> str:
    '''
    >>> get_sufficiently_unique_iri('flipl://iri.example/blarg/?#')
    '://iri.example/blarg'
    >>> get_sufficiently_unique_iri('namly:urn.example:blerg')
    'namly:urn.example:blerg'
    '''
    (_suffuniq_iri, _) = get_sufficiently_unique_iri_and_scheme(iri)
    return _suffuniq_iri


def get_iri_scheme(iri: str) -> str:
    '''
    >>> get_iri_scheme('flipl://iri.example/blarg/?#')
    'flipl'
    >>> get_iri_scheme('namly:urn.example:blerg')
    'namly'
    '''
    (_, _iri_scheme) = get_sufficiently_unique_iri_and_scheme(iri)
    return _iri_scheme


def iris_sufficiently_equal(*iris) -> bool:
    '''
    >>> iris_sufficiently_equal(
    ...  'flipl://iri.example/blarg/blerg/?#',
    ...  'http://iri.example/blarg/blerg',
    ...  'https://iri.example/blarg/blerg',
    ...  'git://iri.example/blarg/blerg',
    ... )
    True
    >>> iris_sufficiently_equal(
    ...  'flipl://iri.example/blarg/blerg',
    ...  'namly:iri.example/blarg/blerg',
    ... )
    False
    >>> iris_sufficiently_equal(
    ...  'namly:urn.example:blerg',
    ...  'namly:urn.example:blerg',
    ... )
    True
    >>> iris_sufficiently_equal(
    ...  'namly:urn.example:blerg',
    ...  'nimly:urn.example:blerg',
    ... )
    False
    '''
    _suffuniq_iris = set(map(get_sufficiently_unique_iri, iris))
    return len(_suffuniq_iris) == 1


def get_sufficiently_unique_iri_and_scheme(iri: str) -> tuple[str, str]:
    '''
    >>> get_sufficiently_unique_iri_and_scheme('flipl://iri.example/blarg/?#')
    ('://iri.example/blarg', 'flipl')
    >>> get_sufficiently_unique_iri_and_scheme('namly:urn.example:blerg')
    ('namly:urn.example:blerg', 'namly')
    '''
    _scheme_match = IRI_SCHEME_REGEX_IGNORECASE.match(iri)
    if _scheme_match:
        _scheme = _scheme_match.group().lower()
        _remainder = iri[_scheme_match.end():]
        if not _remainder.startswith(COLON):
            raise trove_exceptions.IriInvalid(f'does not look like an iri (got "{iri}")')
        if not _remainder.startswith(COLON_SLASH_SLASH):
            # for an iri without '://', assume nothing!
            return (iri, _scheme)
    else:  # may omit scheme only if `://`
        if not iri.startswith(COLON_SLASH_SLASH):
            raise trove_exceptions.IriInvalid(f'does not look like an iri (got "{iri}")')
        _scheme = ''
        _remainder = iri
    # for an iri with '://', is "safe enough" to normalize a little:
    _split_remainder = _urp.urlsplit(_remainder)
    _cleaned_remainder = _urp.urlunsplit((
        '',  # scheme already split
        _split_remainder.netloc,
        _split_remainder.path.rstrip('/'),  # remove trailing slashes
        _split_remainder.query,  # will drop '?' if no querystring
        _split_remainder.fragment,  # will drop '#' if no fragment
    ))
    return (_cleaned_remainder, _scheme)


def is_worthwhile_iri(iri: str):
    '''
    >>> is_worthwhile_iri('flipl://iri.example/blarg/?#')
    True
    >>> is_worthwhile_iri('namly:urn.example:blerg')
    True
    >>> is_worthwhile_iri('_:1234')
    False
    '''
    return (
        isinstance(iri, str)
        and not iri.startswith('_')  # skip artefacts of sharev2 shenanigans
    )


def iri_path_as_keyword(iris: list[str] | tuple[str, ...], *, suffuniq=False) -> str:
    '''return a string-serialized list of iris

    meant for storing in an elasticsearch "keyword" field (happens to use json)
    >>> iri_path_as_keyword(['flipl://iri.example/blarg', 'namly:urn.example:blerg'])
    '["flipl://iri.example/blarg", "namly:urn.example:blerg"]'
    >>> iri_path_as_keyword(
    ...     ['flipl://iri.example/blarg', 'namly:urn.example:blerg'],
    ...     suffuniq=True)
    '["://iri.example/blarg", "namly:urn.example:blerg"]'
    '''
    _list = iris
    if suffuniq:
        _list = [
            get_sufficiently_unique_iri(_iri)
            for _iri in iris
        ]
    return json.dumps(_list)


def unquote_iri(iri: str) -> str:
    '''
    like `urllib.parse.unquote` but recognizes multiply-quoted IRIs
    (unquoting until starting "foo:" or "://", leaving further quoted characters intact)

    >>> unquote_iri('flipl://iri.example/blarg/?#')
    'flipl://iri.example/blarg/?#'
    >>> unquote_iri('flipl%3A//iri.example/blarg/%3F%23')
    'flipl://iri.example/blarg/?#'
    >>> unquote_iri('namly:urn.example:blerg')
    'namly:urn.example:blerg'
    >>> unquote_iri('namly%3Aurn.example%3Ablerg')
    'namly:urn.example:blerg'
    >>> unquote_iri('werbleWord')
    'werbleWord'

    >>> import urllib.parse as _urp
    >>> _unquoted = 'flipl://iri.example/blarg/?' + _urp.urlencode({'param': '://bl@rg?'})
    >>> unquote_iri(_unquoted)
    'flipl://iri.example/blarg/?param=%3A%2F%2Fbl%40rg%3F'
    >>> unquote_iri(_urp.quote(_unquoted))
    'flipl://iri.example/blarg/?param=%3A%2F%2Fbl%40rg%3F'
    >>> unquote_iri(_urp.quote(_urp.quote(_unquoted)))
    'flipl://iri.example/blarg/?param=%3A%2F%2Fbl%40rg%3F'
    >>> unquote_iri(_urp.quote(_urp.quote(_urp.quote(_unquoted))))
    'flipl://iri.example/blarg/?param=%3A%2F%2Fbl%40rg%3F'
    '''
    _unquoted_iri = iri
    while not UNQUOTED_IRI_REGEX.match(_unquoted_iri):
        _next_unquoted_iri = _urp.unquote(_unquoted_iri)
        if _unquoted_iri == _next_unquoted_iri:
            break
        _unquoted_iri = _next_unquoted_iri
    return _unquoted_iri


def smells_like_iri(maybe_iri: str) -> bool:
    '''check a string starts like an IRI (does not fully validate)

    >>> smells_like_iri('https://blarg.example/hello')
    True
    >>> smells_like_iri('foo:bar')  # URN
    True

    >>> smells_like_iri('://blarg.example/hello')
    False
    >>> smells_like_iri('foo/bar')
    False
    >>> smells_like_iri('foo')
    False
    >>> smells_like_iri(7)
    False
    '''
    try:
        return (
            isinstance(maybe_iri, str)
            # nonempty suffuniq-iri and scheme
            and all(get_sufficiently_unique_iri_and_scheme(maybe_iri))
        )
    except trove_exceptions.IriInvalid:
        return False
