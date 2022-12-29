from share.util import rdfutil
from ._base import BaseRdfExtractor


class SimpleRdfParseExtractor(BaseRdfExtractor):
    RDF_FORMAT = None

    def extract_resource_description(self, input_document, resource_uri):
        full_rdfgraph = (
            rdfutil.contextualized_graph()
            .parse(format=self.RDF_FORMAT, data=input_document)
        )
        connected_subgraph = rdfutil.contextualized_graph()
        for triple in rdfutil.connected_subgraph_triples(full_rdfgraph, resource_uri):
            connected_subgraph.add(triple)
        return connected_subgraph


class TurtleRdfExtractor(SimpleRdfParseExtractor):
    RDF_FORMAT = 'turtle'


class JsonldRdfExtractor(SimpleRdfParseExtractor):
    RDF_FORMAT = 'json-ld'
