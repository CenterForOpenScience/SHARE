from django import http
from django.views import View

from trove.openapi import get_trove_openapi_json


class OpenapiJsonView(View):
    def get(self, request):
        return http.HttpResponse(
            content=get_trove_openapi_json(),
            content_type='application/json',
        )


class OpenapiUiView(View):
    def get(self, request):
        return http.HttpResponse(
            content=render_from_rdf(
                _search_gathering.leaf_a_record(),
                _search_iri,
                JSONAPI_MEDIATYPE,
            ),
            content_type=JSONAPI_MEDIATYPE,
        )

