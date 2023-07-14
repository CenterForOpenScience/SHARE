import json

import gather

from trove.vocab.trove import TROVE_VOCAB, trove_labeler, trove_indexcard_namespace
from .jsonapi import RdfJsonapiRenderer


# TODO: common renderer interface, cleaner `render_from_rdf` implementation
# RENDERER_BY_MEDIATYPE = {
#     'application/api+json': RdfJsonapiRenderer,
#     'application/ld+json': RdfJsonldRenderer,
#     'text/turtle': RdfTurtleRenderer,
#     'text/html': RdfHtmlRenderer,
# }


def render_from_rdf(
    rdf_tripledict: gather.RdfTripleDictionary,
    focus_iri: str,
    to_mediatype: str,  # TODO: accept django.http.HttpRequest for content negotiation?
):
    if to_mediatype == 'application/api+json':
        _renderer = RdfJsonapiRenderer(
            data=rdf_tripledict,
            vocabulary=TROVE_VOCAB,
            labeler=trove_labeler,
            id_namespace=trove_indexcard_namespace(),
        )
        return json.dumps(
            _renderer.jsonapi_datum_document(focus_iri),
            indent=2,  # TODO: pretty-print query param?
        )
    raise ValueError(f'unsupported mediatype "{to_mediatype}"')
