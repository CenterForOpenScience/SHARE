from .legacy_sharev2 import LegacySharev2Extractor
from .simple_rdf_parse import SimpleRdfParseExtractor


def get_rdf_extractor(contenttype, source_config):
    if source_config.transformer_key:
        return LegacySharev2Extractor(source_config)
    if contenttype == 'text/turtle':
        return SimpleRdfParseExtractor(source_config, rdf_parser='turtle')
    if contenttype == 'application/ld+json':
        return SimpleRdfParseExtractor(source_config, rdf_parser='json-ld')
    raise NotImplementedError(f'no rdf extractor for content-type: {contenttype}')
