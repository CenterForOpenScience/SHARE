from primitive_metadata import primitive_rdf as rdf

from trove.vocab.namespaces import TROVE
from ._base import BaseRenderer
from .rendering import (
    EntireRendering,
    ProtoRendering,
)


class RdfTurtleRenderer(BaseRenderer):
    MEDIATYPE = 'text/turtle'
    # include indexcard metadata as JSON literals (because QuotedGraph is non-standard)
    INDEXCARD_DERIVER_IRI = TROVE['derive/osfmap_json']

    def render_document(self) -> ProtoRendering:
        return EntireRendering(self.MEDIATYPE, self._render_turtle())

    def _render_turtle(self) -> str:
        return rdf.turtle_from_tripledict(
            self.response_data.tripledict,
            focus=self.response_focus.single_iri(),
            shorthand=self.iri_shorthand,
        )
