from django.views.generic.base import View
from django.template.response import HttpResponse

from share.oaipmh.repository import OAIRepository


class OAIPMHView(View):
    CONTENT_TYPE = 'text/xml'

    def get(self, request):
        return self.oai_response(**request.GET)

    def post(self, request):
        return self.oai_response(**request.POST)

    def oai_response(self, **kwargs):
        repository = OAIRepository()
        xml = repository.handle_request(self.request, kwargs)
        return HttpResponse(xml, content_type=self.CONTENT_TYPE)
