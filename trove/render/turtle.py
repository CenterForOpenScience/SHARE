from primitive_metadata import primitive_rdf as rdf

from trove.vocab.namespaces import TROVE
from ._base import BaseRenderer


class RdfTurtleRenderer(BaseRenderer):
    MEDIATYPE = 'text/turtle'
    # include indexcard metadata as JSON literals (because QuotedGraph is non-standard)
    INDEXCARD_DERIVER_IRI = TROVE['derive/osfmap_json']

    def simple_render_document(self) -> str:
        return rdf.turtle_from_tripledict(
            self.response_data.tripledict,
            focus=self.response_focus_iri,
        )
