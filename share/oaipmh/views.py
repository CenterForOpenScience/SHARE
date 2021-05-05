from django.conf import settings
from django.views.generic.base import View
from django.template.response import HttpResponse

from share.oaipmh.legacy.repository import OAIRepository as LegacyRepository
from share.oaipmh.fmr_repository import OaiPmhRepository
from share.search.elastic_manager import ElasticManager


class OAIPMHView(View):
    CONTENT_TYPE = 'text/xml'

    def get(self, request):
        return self.oai_response(**request.GET)

    def post(self, request):
        return self.oai_response(**request.POST)

    def oai_response(self, **kwargs):
        use_legacy_repository = self._should_use_legacy_repository(kwargs.pop('pls_trove', False))

        if use_legacy_repository:
            repository = LegacyRepository()
        else:
            repository = OaiPmhRepository()

        xml = repository.handle_request(self.request, kwargs)
        return HttpResponse(xml, content_type=self.CONTENT_TYPE)

    def _should_use_legacy_repository(self, pls_trove):
        if pls_trove or not settings.SHARE_LEGACY_PIPELINE:
            return False

        # TEMPORARY HACK -- i mean it this time -- very specific to May 2021
        # check whether the primary elasticsearch alias points at the "old" or "new" index
        primary_indexes = ElasticManager().get_primary_indexes()

        # old index name from settings.ELASTICSEARCH['INDEXES']
        return (primary_indexes == ['share_customtax_1'])
