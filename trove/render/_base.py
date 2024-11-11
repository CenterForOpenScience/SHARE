import abc
import dataclasses
import functools
import json
from typing import ClassVar, Iterable

from django import http as djhttp
from primitive_metadata import primitive_rdf as rdf

from trove import exceptions as trove_exceptions
from trove.vocab import mediatypes
from trove.vocab.namespaces import NAMESPACES_SHORTHAND
from trove.vocab.trove import TROVE_API_THESAURUS


class ProtoRendering:
    @property
    def mediatype(self) -> str:
        raise NotImplementedError

    @property
    def is_streamed(self) -> bool:
        return False

    def iter_content(self) -> Iterable[str | bytes | memoryview]:
        yield from ()


@dataclasses.dataclass
class LiteralRendering(ProtoRendering):
    literal: rdf.Literal

    def iter_content(self):
        yield self.literal.unicode_value


@dataclasses.dataclass
class BaseRenderer(abc.ABC):
    """for rendering an api response modeled as rdf into a serialized http response"""

    # required in subclasses
    MEDIATYPE: ClassVar[str]
    # should be set when render_error_document is overridden:
    ERROR_MEDIATYPE: ClassVar[str] = mediatypes.JSONAPI
    # should be set when the renderer expects a specific derived metadata format
    INDEXCARD_DERIVER_IRI: ClassVar[str | None] = None

    # instance fields
    response_focus_iri: str
    response_data: rdf.RdfTripleDictionary = dataclasses.field(default_factory=dict)
    http_request: djhttp.HttpRequest | None = None
    http_response: djhttp.HttpResponse = dataclasses.field(default_factory=djhttp.HttpResponse)
    iri_shorthand: rdf.IriShorthand = NAMESPACES_SHORTHAND
    thesaurus_tripledict: rdf.RdfTripleDictionary = dataclasses.field(default_factory=lambda: TROVE_API_THESAURUS)

    @functools.cached_property
    def thesaurus(self):
        return rdf.RdfGraph(self.thesaurus_tripledict)

    def render_document(self) -> str | None:
        raise NotImplementedError

    def render_response(self) -> djhttp.HttpResponse:
        self.http_response.content_type = self.MEDIATYPE
        _content = self.render_document()
        if isinstance(_content, str):
            self.http_response.content = _content
        return self.http_response

    def render_error_response(self, error: trove_exceptions.TroveError):
        self.http_response.status = error.http_status
        self.http_response.content_type = self.ERROR_MEDIATYPE
        self.http_response.content = self.render_error_document(error)
        return self.http_response

    def render_error_document(self, error: trove_exceptions.TroveError) -> str:
        # may override, but default to jsonapi
        return json.dumps(
            {'errors': [{  # https://jsonapi.org/format/#error-objects
                'status': error.http_status,
                'code': error.error_location,
                'title': error.__class__.__name__,
                'detail': str(error),
            }]},
            indent=2,
        )
