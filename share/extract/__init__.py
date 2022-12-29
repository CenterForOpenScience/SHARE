from ._base import BaseRdfExtractor
from .legacy_sharev2 import LegacySharev2Extractor
from .simple_rdf_parse import TurtleRdfExtractor, JsonldRdfExtractor


__all__ = ('get_rdf_extractor_class',)


def get_rdf_extractor_class(contenttype) -> type[BaseRdfExtractor]:
    if contenttype is None:
        return LegacySharev2Extractor
    if contenttype == 'text/turtle':
        return TurtleRdfExtractor
    if contenttype == 'application/ld+json':
        return JsonldRdfExtractor
    raise NotImplementedError(f'no rdf extractor for content-type: {contenttype}')
