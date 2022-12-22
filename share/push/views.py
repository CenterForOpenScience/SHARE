from django.http import HttpResponse
from rest_framework import views

from share import exceptions
from share.util import rdfutil
from share.util.ingester import Ingester


class RdfPushView(views.APIView):
    def get(self, request):
        pass  # TODO: show this user's most recently pushed rdf for this pid

    def put(self, request, pid):
        # TODO: permissions, validate pid against user source
        try:
            ingester = Ingester(
                request.data,
                rdfutil.normalize_pid_url(pid),
                contenttype=request.content_type,
            ).as_user(request.user)
            ingester.ingest_async()
        except exceptions.IngestError as e:
            return HttpResponse(str(e), status=400)
        else:
            return HttpResponse(status=201)
