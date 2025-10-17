import abc
import dataclasses
import functools
import json
from typing import ClassVar

from primitive_metadata import (
    gather,
    primitive_rdf as rdf,
)

from trove import exceptions as trove_exceptions
from trove.vocab import mediatypes
from trove.vocab.trove import TROVE_API_THESAURUS
from trove.vocab.namespaces import namespaces_shorthand
from .rendering import ProtoRendering, EntireRendering


@dataclasses.dataclass
class BaseRenderer(abc.ABC):
    """for creating a serialized rendering of an api response modeled as rdf"""

    # required in subclasses
    MEDIATYPE: ClassVar[str]
    # should be set when the renderer expects a specific derived metadata format
    INDEXCARD_DERIVER_IRI: ClassVar[str | None] = None
    # when True, the renderer renders only what's already been gathered
    # (set False if the renderer knows what to request)
    PASSIVE_RENDER: ClassVar[bool] = True

    # instance fields
    response_focus: gather.Focus
    response_gathering: gather.Gathering
    iri_shorthand: rdf.IriShorthand = dataclasses.field(default_factory=namespaces_shorthand)
    thesaurus_tripledict: rdf.RdfTripleDictionary = dataclasses.field(default_factory=lambda: TROVE_API_THESAURUS)

    @classmethod
    def get_deriver_iri(cls, card_blending: bool) -> str | None:
        # override if needed
        return cls.INDEXCARD_DERIVER_IRI

    @functools.cached_property
    def thesaurus(self) -> 'rdf.RdfGraph':
        return rdf.RdfGraph(self.thesaurus_tripledict)

    @functools.cached_property
    def response_data(self) -> 'rdf.RdfGraph':
        return rdf.RdfGraph(self.response_tripledict)

    @functools.cached_property
    def response_tripledict(self) -> rdf.RdfTripleDictionary:
        # TODO: self.response_gathering.ask_all_about or a default ask...
        return self.response_gathering.leaf_a_record()

    def simple_render_document(self) -> str | bytes:
        raise NotImplementedError

    def render_document(self) -> ProtoRendering:
        try:
            _content = self.simple_render_document()
        except NotImplementedError:
            raise NotImplementedError(f'class "{type(self)}" must implement either `render_document` or `simple_render_document`')
        else:
            return EntireRendering(
                mediatype=self.MEDIATYPE,
                entire_content=_content,
            )

    @classmethod
    def render_error_document(cls, error: trove_exceptions.TroveError) -> ProtoRendering:
        # may override, but default to jsonapi
        return EntireRendering(
            mediatype=mediatypes.JSONAPI,
            entire_content=json.dumps(
                {'errors': [{  # https://jsonapi.org/format/#error-objects
                    'status': error.http_status,
                    'code': error.error_location,
                    'title': error.__class__.__name__,
                    'detail': str(error),
                }]},
                indent=2,
            ),
        )
