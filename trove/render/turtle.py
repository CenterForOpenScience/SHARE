from primitive_metadata.primitive_rdf import turtle_from_tripledict

from ._base import BaseRenderer


class RdfTurtleRenderer(BaseRenderer):
    MEDIATYPE = 'text/turtle'

    def render_document(self, rdf_graph, focus_iri):
        return turtle_from_tripledict(rdf_graph, focus=focus_iri)
