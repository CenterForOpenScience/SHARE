from primitive_metadata import primitive_rdf as rdf

from trove.vocab.namespaces import TROVE
from ._base import BaseRenderer


class RdfTurtleRenderer(BaseRenderer):
    MEDIATYPE = 'text/turtle'
    INDEXCARD_DERIVER_IRI = TROVE['derive/osfmap_json']

    def render_document(self, rdf_graph: rdf.RdfGraph, focus_iri: str):
        return rdf.turtle_from_tripledict(rdf_graph.tripledict, focus=focus_iri)
