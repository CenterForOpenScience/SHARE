import abc
import json
from typing import Optional, ClassVar

from django import http
from primitive_metadata import primitive_rdf as rdf

from trove import exceptions as trove_exceptions
from trove.vocab import mediatypes


class BaseRenderer(abc.ABC):
    # required in subclasses
    MEDIATYPE: ClassVar[str]
    # should be set when render_error_document is overridden:
    ERROR_MEDIATYPE: ClassVar[str] = mediatypes.JSONAPI
    # should be set when the renderer expects a specific derived metadata format
    INDEXCARD_DERIVER_IRI: ClassVar[str | None] = None

    def __init__(
        self, *,
        iri_shorthand: rdf.IriShorthand,
        thesaurus: rdf.RdfTripleDictionary,
        request: Optional[http.HttpRequest] = None,
    ):
        self.iri_shorthand = iri_shorthand
        self.thesaurus = rdf.RdfGraph(thesaurus)
        self.request = request

    def render_response(
        self,
        response_data: rdf.RdfTripleDictionary,
        response_focus_iri: str,
        **response_kwargs,
    ):
        return http.HttpResponse(
            content=self.render_document(rdf.RdfGraph(response_data), response_focus_iri),
            content_type=self.MEDIATYPE,
            **response_kwargs,
        )

    def render_error_response(self, error: trove_exceptions.TroveError):
        return http.HttpResponse(
            content=self.render_error_document(error),
            content_type=self.ERROR_MEDIATYPE,
            status=error.http_status,
        )

    @abc.abstractmethod
    def render_document(self, data: rdf.RdfGraph, focus_iri: str) -> str:
        raise NotImplementedError

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
