from share.legacy_normalize.regulate import Regulator
from share.util import sharev2_to_rdf
from ._base import BaseRdfExtractor


class LegacySharev2Extractor(BaseRdfExtractor):
    def extract_resource_description(self, input_document, resource_uri):
        transformer = self.source_config.get_transformer()
        sharev2graph = transformer.transform(input_document)
        if sharev2graph:
            Regulator(source_config=self.source_config).regulate(sharev2graph)
        return sharev2_to_rdf.convert(sharev2graph, resource_uri)
