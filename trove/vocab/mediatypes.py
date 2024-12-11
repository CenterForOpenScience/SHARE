JSON = 'application/json'
JSONAPI = 'application/vnd.api+json'
JSONLD = 'application/ld+json'
TURTLE = 'text/turtle'
HTML = 'text/html'
TSV = 'text/tab-separated-values'
CSV = 'text/csv'


_file_extensions = {
    JSON: '.json',
    JSONAPI: '.json',
    JSONLD: '.json',
    TURTLE: '.turtle',
    HTML: '.html',
    TSV: '.tsv',
    CSV: '.csv',
}


def dot_extension(mediatype: str) -> str:
    try:
        return _file_extensions[mediatype]
    except KeyError:
        raise ValueError(f'unrecognized mediatype: {mediatype}')
