import abc
import dataclasses
import functools
import json
from typing import ClassVar

from primitive_metadata import primitive_rdf as rdf

from trove import exceptions as trove_exceptions
from trove.vocab import mediatypes
from trove.vocab.namespaces import NAMESPACES_SHORTHAND
from trove.vocab.trove import TROVE_API_THESAURUS
from ._rendering import ProtoRendering, SimpleRendering


@dataclasses.dataclass
class BaseRenderer(abc.ABC):
    """for rendering an api response modeled as rdf into a serialized http response"""

    # required in subclasses
    MEDIATYPE: ClassVar[str]
    # should be set when the renderer expects a specific derived metadata format
    INDEXCARD_DERIVER_IRI: ClassVar[str | None] = None

    # instance fields
    response_focus_iri: str
    response_tripledict: rdf.RdfTripleDictionary = dataclasses.field(default_factory=dict)
    iri_shorthand: rdf.IriShorthand = NAMESPACES_SHORTHAND
    thesaurus_tripledict: rdf.RdfTripleDictionary = dataclasses.field(default_factory=lambda: TROVE_API_THESAURUS)

    @functools.cached_property
    def thesaurus(self):
        return rdf.RdfGraph(self.thesaurus_tripledict)

    @functools.cached_property
    def response_data(self):
        return rdf.RdfGraph(self.response_tripledict)

    def simple_render_document(self) -> str:
        raise NotImplementedError

    def render_document(self) -> ProtoRendering:
        try:
            _content = self.simple_render_document()
        except NotImplementedError:
            raise NotImplementedError(f'class "{type(self)}" must implement either `render_document` or `simple_render_document`')
        else:
            return SimpleRendering(
                mediatype=self.MEDIATYPE,
                rendered_content=_content,
            )

    def render_error_document(self, error: trove_exceptions.TroveError) -> ProtoRendering:
        # may override, but default to jsonapi
        return SimpleRendering(
            mediatype=mediatypes.JSONAPI,
            rendered_content=json.dumps(
                {'errors': [{  # https://jsonapi.org/format/#error-objects
                    'status': error.http_status,
                    'code': error.error_location,
                    'title': error.__class__.__name__,
                    'detail': str(error),
                }]},
                indent=2,
            ),
        )
