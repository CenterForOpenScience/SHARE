import abc
from typing import Optional, ClassVar

from django import http
from primitive_metadata import primitive_rdf as rdf


class BaseRenderer(abc.ABC):
    MEDIATYPE: ClassVar[str]  # required in subclasses

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
            content=self.render_document(response_data, response_focus_iri),
            content_type=self.MEDIATYPE,
            **response_kwargs,
        )

    @abc.abstractmethod
    def render_document(self, data: rdf.RdfTripleDictionary, focus_iri: str) -> str:
        raise NotImplementedError
