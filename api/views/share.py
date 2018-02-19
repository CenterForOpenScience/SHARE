from rest_framework import views
from rest_framework.response import Response

from django import http
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.views.generic.base import RedirectView

from share.models import Source

from api import util


@require_GET
def source_icon_view(request, source_name):
    source = get_object_or_404(Source, name=source_name)
    if not source.icon:
        raise http.Http404('Favicon for source {} does not exist'.format(source_name))
    response = http.HttpResponse(source.icon)
    response['Content-Type'] = 'image/x-icon'
    return response


class APIVersionRedirectView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        return '/api/v2/{}'.format(kwargs['path'])

    def get(self, request, *args, **kwargs):
        url = self.get_redirect_url(*args, **kwargs)
        if url:
            if self.permanent:
                return util.HttpSmartResponsePermanentRedirect(url)
            return util.HttpSmartResponseRedirect(url)
        return http.HttpResponseGone()


class ServerStatusView(views.APIView):
    def get(self, request):
        return Response({
            'id': '1',
            'type': 'Status',
            'attributes': {
                'status': 'up',
                'version': settings.VERSION,
            }
        })
