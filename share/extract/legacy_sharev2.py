from share.legacy_normalize.regulate import Regulator
from share.util.sharev2_to_rdf import sharev2_to_rdf
from ._base import BaseRdfExtractor


class LegacySharev2Extractor(BaseRdfExtractor):
    def extract_resource_description(self, input_document, focus_uri):
        transformer = self.source_config.get_transformer()
        sharev2graph = transformer.transform(input_document)
        if not sharev2graph:
            return None
        Regulator(source_config=self.source_config).regulate(sharev2graph)
        if not sharev2graph:
            return None
        central_node = sharev2graph.get_central_node(guess=True)
        if central_node is None or central_node['is_deleted']:
            return None
        (_, rdfgraph) = sharev2_to_rdf(sharev2graph, focus_uri)
        return rdfgraph
