from urllib.parse import urlparse


# TODO leave URNs alone, do scheme:authority:path instead of scheme://authority/path
URN_SCHEMES = frozenset({'urn', 'oai'})


def parse(iri):
    """Parse an IRI string into its constituent parts.
    """
    scheme, _, remainder = iri.partition(':')
    if scheme.lower() in URN_SCHEMES:
        if remainder.startswith('//'):
            # Handle our own brand of slashed up URNs
            authority, _, remainder = remainder.lstrip('/').partition('/')
        else:
            # Technically, everything past 'urn:' is the path, but the next segment is usually an authority of some sort
            authority, _, remainder = remainder.partition(':')
        return {
            'scheme': scheme,
            'authority': authority,
            'path': '/{}'.format(remainder),
            'IRI': iri,
        }
    # If it doesn't have a URN scheme, assume it's a URL
    parsed = urlparse(iri)
    return {
        'scheme': parsed.scheme,
        'authority': parsed.netloc,
        'path': parsed.path,
        'query': parsed.query,
        'fragment': parsed.fragment,
        'IRI': iri,
    }


def compose(scheme, authority, path, **kwargs):
    """Build an IRI out of constituent parts.
    """

    return '{scheme}://{authority}{path}{query}{fragment}'.format(
        scheme=scheme,
        authority=authority,
        path=path,
        query='?{}'.format(kwargs['query']) if kwargs.get('query') else '',
        fragment='#{}'.format(kwargs['fragment']) if kwargs.get('fragment') else '',
    )
