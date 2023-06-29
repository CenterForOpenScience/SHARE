from ._base import BaseRdfExtractor
from .legacy_sharev2 import LegacySharev2Extractor
from .turtle import TurtleRdfExtractor


__all__ = ('get_rdf_extractor_class',)


def get_rdf_extractor_class(mediatype) -> type[BaseRdfExtractor]:
    if mediatype is None:
        return LegacySharev2Extractor
    if mediatype == 'text/turtle':
        return TurtleRdfExtractor
    raise NotImplementedError(f'no rdf extractor for media-type "{mediatype}"')
