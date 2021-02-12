from django.conf import settings
from django.views.generic.base import View
from django.template.response import HttpResponse

from share.oaipmh.legacy.repository import OAIRepository as LegacyRepository
from share.oaipmh.fmr_repository import OaiPmhRepository


class OAIPMHView(View):
    CONTENT_TYPE = 'text/xml'

    def get(self, request):
        return self.oai_response(**request.GET)

    def post(self, request):
        return self.oai_response(**request.POST)

    def oai_response(self, **kwargs):
        use_legacy_pipeline = (
            settings.SHARE_LEGACY_PIPELINE
            and not kwargs.pop('pls_trove', False)
        )
        if use_legacy_pipeline:
            repository = LegacyRepository()
        else:
            repository = OaiPmhRepository()

        xml = repository.handle_request(self.request, kwargs)
        return HttpResponse(xml, content_type=self.CONTENT_TYPE)
