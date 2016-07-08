import requests
from rest_framework import views, permissions
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from furl import furl
from rest_framework.response import Response


class ElasticSearchView(views.APIView):
    permission_classes = []

    def get(self, request, *args, url_bits='', **kwargs):
        es_url = furl(settings.ELASTICSEARCH_URL).add(
            path=settings.ELASTICSEARCH_INDEX,
            query_params=request.query_params,
        ).add(path=url_bits.split('/'))
        resp = requests.get(es_url)
        return Response(data=resp.json(), headers={'Content-Type': 'application/json'})

    @method_decorator(csrf_exempt)
    def post(self, request, *args, url_bits='', **kwargs):
        es_url = furl(settings.ELASTICSEARCH_URL).add(
            path=settings.ELASTICSEARCH_INDEX,
            query_params=request.query_params,
        ).add(path=url_bits.split('/'))
        resp = requests.post(es_url, json=request.data)
        return Response(data=resp.json(), headers={'Content-Type': 'application/json'})
