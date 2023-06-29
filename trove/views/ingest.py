import logging

from django import http
from django.views import View

from share import exceptions
from trove import digestive_tract


logger = logging.getLogger(__name__)


class RdfIngestView(View):
    def get(self, request):
        # TODO: something? maybe show this user's most recently pushed rdf for this pid
        raise NotImplementedError

    def post(self, request):
        # TODO: better error responses (jsonapi? shacl:ValidationReport?)
        # TODO: permissions, validate focus_iri domain with user Source?
        if not request.user.is_authenticated:
            breakpoint()
            return http.HttpResponse(status=401)
        _focus_iri = request.GET.get('focus_iri')
        if not _focus_iri:
            return http.HttpResponse('focus_iri queryparam required', status=400)
        _record_identifier = request.GET.get('record_identifier')
        if not _record_identifier:
            return http.HttpResponse('record_identifier queryparam required', status=400)
        try:
            digestive_tract.swallow(
                from_user=request.user,
                record=request.body.decode(encoding='utf-8'),
                record_identifier=_record_identifier,
                record_mediatype=request.content_type,
                resource_iri=_focus_iri,
            )
        except exceptions.IngestError as e:
            logger.exception(str(e))
            return http.HttpResponse(str(e), status=400)
        else:
            # TODO: include link to view ingestjob status (returned by `swallow`)
            return http.HttpResponse(status=201)
