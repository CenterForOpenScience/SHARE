import json
import re
from urllib.parse import urlsplit, urlunsplit


# quoth <https://www.rfc-editor.org/rfc/rfc3987.html#section-2.2>:
#   scheme = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )
IRI_SCHEME_REGEX = re.compile(
    r'[a-z]'            # one letter from the english alphabet
    r'[a-z0-9+-.]*'     # zero or more letters, decimal numerals, or the symbols `+`, `-`, or `.`
)
IRI_SCHEME_REGEX_IGNORECASE = re.compile(IRI_SCHEME_REGEX.pattern, flags=re.IGNORECASE)
COLON = ':'
COLON_SLASH_SLASH = '://'

# treat similar-enough IRIs as equivalent, based on a wild assertion:
#   if two IRIs differ only in their `scheme`
#   and have non-empty `authority` component,
#   they may safely be considered equivalent.
# (while this is not strictly true, it should be true enough and helps avoid
# hand-wringing about "http" vs "https" -- use either or both, it's fine)


def get_sufficiently_unique_iri(iri: str) -> str:
    (_suffuniq_iri, _) = get_sufficiently_unique_iri_and_scheme(iri)
    return _suffuniq_iri


def get_sufficiently_unique_iri_and_scheme(iri: str) -> tuple[str, str]:
    _scheme_match = IRI_SCHEME_REGEX_IGNORECASE.match(iri)
    if not _scheme_match:
        raise ValueError(f'does not look like an iri (got "{iri}")')
    _scheme = _scheme_match.group().lower()
    _remainder = iri[_scheme_match.end():]
    if not _remainder.startswith(COLON_SLASH_SLASH):
        # for an iri without '://', assume nothing!
        return (iri, _scheme)
    # for an iri with '://', is "safe enough" to normalize a little:
    _split_remainder = urlsplit(_remainder)
    _cleaned_remainder = urlunsplit((
        '',  # scheme already split
        _split_remainder.netloc,
        _split_remainder.path.rstrip('/'),  # remove trailing slashes
        _split_remainder.query,  # will drop '?' if no querystring
        _split_remainder.fragment,  # will drop '#' if no fragment
    ))
    return (_cleaned_remainder, _scheme)


def is_worthwhile_iri(iri: str):
    return (
        isinstance(iri, str)
        and not iri.startswith('_')  # skip artefacts of sharev2 shenanigans
    )


def iri_path_as_keyword(iris: list[str] | tuple[str], *, suffuniq=False) -> str:
    assert isinstance(iris, (list, tuple)) and all(
        isinstance(_pathstep, str)
        for _pathstep in iris
    ), f'expected list or tuple of str, got {iris}'
    _list = iris
    if suffuniq:
        _list = [
            get_sufficiently_unique_iri(_iri)
            for _iri in iris
        ]
    return json.dumps(_list)
