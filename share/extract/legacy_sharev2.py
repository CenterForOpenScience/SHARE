from share.legacy_normalize.regulate import Regulator
from share.util import rdfutil
from ._base import BaseRdfExtractor


class LegacySharev2Extractor(BaseRdfExtractor):
    last_mgraph = None

    def extract_rdf(self, input_str):
        transformer = self.source_config.get_transformer()
        mgraph = transformer.transform(input_str)
        if not mgraph:
            return None
        Regulator(source_config=self.source_config).regulate(mgraph)
        if not mgraph:
            return None
        self.last_mgraph = mgraph
        central_node = mgraph.get_central_node(guess=True)
        if central_node is None or central_node['is_deleted']:
            return None
        return rdfutil.Sharev2ToRdf(mgraph).rdfgraph
