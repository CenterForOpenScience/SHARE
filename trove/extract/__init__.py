from trove import exceptions as trove_exceptions

from ._base import BaseRdfExtractor
from .legacy_sharev2 import LegacySharev2Extractor
from .turtle import TurtleRdfExtractor


__all__ = ('get_rdf_extractor_class',)


def get_rdf_extractor_class(mediatype) -> type[BaseRdfExtractor]:
    if mediatype is None:
        return LegacySharev2Extractor
    if mediatype == 'text/turtle':
        return TurtleRdfExtractor
    raise trove_exceptions.CannotDigestMediatype(mediatype)
