import requests
from rest_framework import views
from django.conf import settings
from furl import furl
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api import authentication


class ElasticSearchView(views.APIView):
    authentication_classes = [authentication.NonCSRFSessionAuthentication, ]
    permission_classes = [AllowAny, ]

    def get(self, request, *args, url_bits='', **kwargs):
        es_url = furl(settings.ELASTICSEARCH_URL).add(
            path=settings.ELASTICSEARCH_INDEX,
            query_params=request.query_params,
        ).add(path=url_bits.split('/'))
        resp = requests.get(es_url)
        return Response(data=resp.json(), headers={'Content-Type': 'application/json'})

    def post(self, request, *args, url_bits='', **kwargs):
        es_url = furl(settings.ELASTICSEARCH_URL).add(
            path=settings.ELASTICSEARCH_INDEX,
            query_params=request.query_params,
        ).add(path=url_bits.split('/'))
        resp = requests.post(es_url, json=request.data)
        return Response(data=resp.json(), headers={'Content-Type': 'application/json'})
