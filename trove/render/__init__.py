from django import http
from gather import primitive_rdf

from trove.vocab.trove import TROVE_API_VOCAB, trove_indexcard_namespace
from .jsonapi import RdfJsonapiRenderer
from .html_browse import RdfHtmlBrowseRenderer


# TODO: common renderer interface, cleaner `render_from_rdf` implementation
# RENDERER_BY_MEDIATYPE = {
#     'application/api+json': RdfJsonapiRenderer,
#     'application/ld+json': RdfJsonldRenderer,
#     'text/turtle': RdfTurtleRenderer,
#     'text/html': RdfHtmlRenderer,
# }


def get_renderer(request: http.HttpRequest, data: primitive_rdf.RdfTripleDictionary):
    if request.accepts(RdfHtmlBrowseRenderer.MEDIATYPE):
        return RdfHtmlBrowseRenderer(
            data=data,
            # TODO: iri_shorthand=...
        )
    if request.accepts(RdfJsonapiRenderer.MEDIATYPE):
        return RdfJsonapiRenderer(
            data=data,
            jsonapi_vocab=TROVE_API_VOCAB,
            id_namespace_set=[trove_indexcard_namespace()],
        )
    raise ValueError(f'could not find renderer for {request}')


def render_response(
    request: http.HttpRequest,
    response_data: primitive_rdf.RdfTripleDictionary,
    response_focus_iri: str,
    **response_kwargs,
):
    _renderer = get_renderer(request, response_data)
    return http.HttpResponse(
        content=_renderer.render_document(response_focus_iri),
        content_type=_renderer.MEDIATYPE,
        **response_kwargs,
    )
