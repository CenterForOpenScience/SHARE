from primitive_metadata import primitive_rdf as rdf

from ._base import BaseRenderer


class RdfTurtleRenderer(BaseRenderer):
    MEDIATYPE = 'text/turtle'

    def render_document(self, rdf_graph: rdf.RdfGraph, focus_iri: str):
        return rdf.turtle_from_tripledict(rdf_graph.tripledict, focus=focus_iri)
