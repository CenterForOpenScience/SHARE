from django import http
from django.views import View

from trove.openapi import get_trove_openapi_json


class OpenapiJsonView(View):
    def get(self, request):
        return http.HttpResponse(
            content=get_trove_openapi_json(),
            content_type='application/json',
        )
