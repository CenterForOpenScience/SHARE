import abc
from typing import Optional

from django import http
from primitive_metadata import primitive_rdf

from trove.vocab.namespaces import STATIC_SHORTHAND


class BaseRenderer(abc.ABC):
    MEDIATYPE = None  # override in subclasses

    def __init__(
        self, *,
        request: Optional[http.HttpRequest] = None,
        iri_shorthand: Optional[primitive_rdf.IriShorthand] = None,
    ):
        self.request = request
        self.iri_shorthand = iri_shorthand or STATIC_SHORTHAND

    def render_response(
        self,
        response_data: primitive_rdf.RdfTripleDictionary,
        response_focus_iri: str,
        **response_kwargs,
    ):
        return http.HttpResponse(
            content=self.render_document(response_data, response_focus_iri),
            content_type=self.MEDIATYPE,
            **response_kwargs,
        )

    @abc.abstractmethod
    def render_document(self, data: primitive_rdf.RdfTripleDictionary, focus_iri: str) -> str:
        raise NotImplementedError
