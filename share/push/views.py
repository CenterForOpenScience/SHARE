from django.http import HttpResponse
from rest_framework import views

from share import exceptions
from share.util import rdfutil
from share.push import ingest


class RdfPushView(views.APIView):
    def get(self, request):
        pass  # TODO: show this user's most recently pushed rdf for this pid

    def put(self, request, pid):
        # TODO: permissions, validate pid against user source
        try:
            suid = ingest.chew(
                datum=request.data,
                datum_identifier=rdfutil.normalize_pid_url(pid),
                datum_contenttype=request.content_type,
                user=request.user,
                urgent=True,
            )
            ingest.swallow(suid, urgent=True)
        except exceptions.IngestError as e:
            return HttpResponse(str(e), status=400)
        else:
            return HttpResponse(status=201)
