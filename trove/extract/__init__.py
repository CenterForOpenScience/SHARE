from trove import exceptions as trove_exceptions

from ._base import BaseRdfExtractor
from .turtle import TurtleRdfExtractor


__all__ = ('get_rdf_extractor_class',)


def get_rdf_extractor_class(mediatype: str) -> type[BaseRdfExtractor]:
    if mediatype == 'text/turtle':
        return TurtleRdfExtractor
    raise trove_exceptions.CannotDigestMediatype(mediatype)
