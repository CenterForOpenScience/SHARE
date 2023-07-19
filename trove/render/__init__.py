import json

import gather

from trove.vocab.trove import TROVE_API_VOCAB, trove_labeler, trove_indexcard_namespace
from .jsonapi import RdfJsonapiRenderer


# TODO: common renderer interface, cleaner `render_from_rdf` implementation
# RENDERER_BY_MEDIATYPE = {
#     'application/api+json': RdfJsonapiRenderer,
#     'application/ld+json': RdfJsonldRenderer,
#     'text/turtle': RdfTurtleRenderer,
#     'text/html': RdfHtmlRenderer,
# }

JSONAPI_MEDIATYPE = 'application/api+json'


def render_from_rdf(
    rdf_tripledict: gather.RdfTripleDictionary,
    focus_iri: str,
    to_mediatype: str,  # TODO: accept django.http.HttpRequest for content negotiation? (and return HttpResponse??)
):
    if to_mediatype == JSONAPI_MEDIATYPE:
        _renderer = RdfJsonapiRenderer(
            data=rdf_tripledict,
            vocabulary=TROVE_API_VOCAB,
            labeler=trove_labeler,
            id_namespace_set=[trove_indexcard_namespace()],
        )
        return json.dumps(
            _renderer.jsonapi_data_document(focus_iri),
            indent=2,  # TODO: pretty-print query param?
        )
    raise ValueError(f'unsupported mediatype "{to_mediatype}"')
