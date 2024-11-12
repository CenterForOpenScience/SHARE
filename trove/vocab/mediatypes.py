JSON = 'application/json'
JSONAPI = 'application/vnd.api+json'
JSONLD = 'application/ld+json'
TURTLE = 'text/turtle'
HTML = 'text/html'
TAB_SEPARATED_VALUES = 'text/tab-separated-values'
COMMA_SEPARATED_VALUES = 'text/csv'


_file_extensions = {
    JSON: 'json',
    JSONAPI: 'json',
    JSONLD: 'json',
    TURTLE: 'turtle',
    HTML: 'html',
    TAB_SEPARATED_VALUES: 'tsv',
    COMMA_SEPARATED_VALUES: 'csv',
}


def get_file_extension(mediatype: str) -> str | None:
    return _file_extensions.get(mediatype)
