import logging

from django.http import HttpResponse
from django.views import View

from share import exceptions
from share.util import rdfutil
from share.push import ingest


logger = logging.getLogger(__name__)


class RdfPushView(View):
    def get(self, request):
        pass  # TODO: show this user's most recently pushed rdf for this pid

    def put(self, request, pid):
        if not request.user:
            raise Exception('no user')
        # TODO: permissions, validate pid against user source
        try:
            suid = ingest.chew(
                datum=request.body,
                datum_identifier=str(rdfutil.normalize_pid_uri(pid)),
                datum_contenttype=request.content_type,
                user=request.user,
            )
            ingest.swallow(suid)
        except exceptions.IngestError as e:
            logger.exception(str(e))
            return HttpResponse(str(e), status=400)
        else:
            return HttpResponse(status=201)
