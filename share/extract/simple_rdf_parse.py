from share.util import rdfutil
from ._base import BaseRdfExtractor


class SimpleRdfParseExtractor(BaseRdfExtractor):
    def __init__(self, *args, rdf_format, **kwargs):
        self._rdf_format = rdf_format
        return super().__init__(*args, **kwargs)

    def extract_resource_description(self, input_document, focus_uri):
        full_rdfgraph = (
            rdfutil.contextualized_graph()
            .parse(format=self._rdf_format, data=input_document)
        )
        connected_subgraph = rdfutil.contextualized_graph()
        self._extract_connected_subgraph(full_rdfgraph, connected_subgraph, focus_uri)
        return connected_subgraph

    def _extract_connected_subgraph(self, from_rdfgraph, into_rdfgraph, triple_subj):
        to_visit_next = set()
        for (triple_pred, triple_obj) in from_rdfgraph.predicate_objects(triple_subj):
            triple = (triple_subj, triple_pred, triple_obj)
            if triple not in into_rdfgraph:
                into_rdfgraph.add(triple)
                to_visit_next.add(triple_pred)
                to_visit_next.add(triple_obj)
        for uri in to_visit_next:
            self._extract_connected_subgraph(from_rdfgraph, into_rdfgraph, uri)
        return into_rdfgraph
