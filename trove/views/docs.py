from django.http import HttpResponse
from django.template.response import SimpleTemplateResponse
from django.views import View

from trove.openapi import get_trove_openapi_json


class OpenapiJsonView(View):
    def get(self, request):
        return HttpResponse(
            content=get_trove_openapi_json(),
            content_type='application/json',
        )


class OpenapiHtmlView(View):
    def get(self, request):
        # TODO: parameterize title, openapi.json url
        return SimpleTemplateResponse('trove/openapi-redoc.html')
