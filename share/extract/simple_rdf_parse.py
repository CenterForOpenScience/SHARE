from share.util import rdfutil
from ._base import BaseRdfExtractor


class SimpleRdfParseExtractor(BaseRdfExtractor):
    def __init__(self, *args, rdf_format, **kwargs):
        self._rdf_format = rdf_format
        return super().__init__(*args, **kwargs)

    def extract_resource_description(self, input_document, focus_uri):
        focus_uri = rdfutil.normalize_pid_uri(focus_uri)
        full_rdfgraph = (
            rdfutil.contextualized_graph()
            .parse(format=self._rdf_format, data=input_document)
        )
        connected_subgraph = rdfutil.contextualized_graph()
        for triple in rdfutil.connected_subgraph_triples(full_rdfgraph, focus_uri):
            connected_subgraph.add(triple)
        return connected_subgraph
