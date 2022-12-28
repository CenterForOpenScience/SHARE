import rdflib

from share.util import rdfutil
from ._base import BaseRdfExtractor


class SimpleRdfParseExtractor(BaseRdfExtractor):
    def __init__(self, source_config, input_document, rdf_format):
        self.rdf_format = rdf_format
        self._rdfgraph = None
        return super().__init__(source_config, input_document)

    @property
    def rdfgraph(self):
        if self._rdfgraph is None:
            self._rdfgraph = (
                rdfutil.contextualized_graph()
                .parse(format=self.rdf_format, data=self.input_document)
            )
        return self._rdfgraph

    def extract_resource_identifiers(self):
        for subj in self.rdfgraph.subjects(unique=True):
            if isinstance(subj, rdflib.URIRef):
                yield subj

    def extract_resource_description(self, input_document, resource_identifier):
        focus_uri = rdfutil.normalize_pid_uri(resource_identifier)
        connected_subgraph = rdfutil.contextualized_graph()
        for triple in rdfutil.connected_subgraph_triples(self.rdfgraph, focus_uri):
            connected_subgraph.add(triple)
        return connected_subgraph
