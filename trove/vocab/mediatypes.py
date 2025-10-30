JSON = 'application/json'
JSONAPI = 'application/vnd.api+json'
JSONLD = 'application/ld+json'
TURTLE = 'text/turtle'
HTML = 'text/html'
TSV = 'text/tab-separated-values'
CSV = 'text/csv'
RSS = 'application/rss+xml'
ATOM = 'application/atom+xml'


_file_extensions = {
    JSON: '.json',
    JSONAPI: '.json',
    JSONLD: '.json',
    TURTLE: '.turtle',
    HTML: '.html',
    TSV: '.tsv',
    CSV: '.csv',
    RSS: '.xml',
    ATOM: '.xml',
}

_PARAMETER_DELIMITER = ';'


def strip_mediatype_parameters(mediatype: str) -> str:
    """from a full mediatype that may have parameters, get only the base mediatype

    >>> strip_mediatype_parameters('text/plain;charset=utf-8')
    'text/plain'
    >>> strip_mediatype_parameters('text/plain')
    'text/plain'

    note: does not validate that the mediatype exists or makes sense
    >>> strip_mediatype_parameters('application/whatever ; blarg=foo')
    'application/whatever'
    """
    (_base, _, __) = mediatype.partition(_PARAMETER_DELIMITER)
    return _base.strip()


def dot_extension(mediatype: str) -> str:
    try:
        return _file_extensions[strip_mediatype_parameters(mediatype)]
    except KeyError:
        raise ValueError(f'unrecognized mediatype: {mediatype}')
