import requests
from rest_framework import views
from django.conf import settings
from furl import furl
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser

from api import authentication


class ElasticSearchView(views.APIView):
    """
    Elasticsearch endpoint for SHARE Data.

    - [Creative Works](/api/search/creativeworks/_search) - Search individual documents harvested
    - [Agents](/api/search/agents/_search) - Search agents from havested documents
    - [Tags](/api/search/tag/_search) - Tags placed on documents
    - [Sources](/api/search/source/_search) - Data sources
    """
    authentication_classes = (authentication.NonCSRFSessionAuthentication, )
    parser_classes = (JSONParser,)
    permission_classes = (AllowAny, )
    renderer_classes = (JSONRenderer, )

    def get(self, request, *args, url_bits='', **kwargs):
        es_url = furl(settings.ELASTICSEARCH_URL).add(
            path=settings.ELASTICSEARCH_INDEX,
            query_params=request.query_params,
        ).add(path=url_bits.split('/'))
        resp = requests.get(es_url)
        return Response(status=resp.status_code, data=resp.json(), headers={'Content-Type': 'application/vand.api+json'})

    def post(self, request, *args, url_bits='', **kwargs):
        es_url = furl(settings.ELASTICSEARCH_URL).add(
            path=settings.ELASTICSEARCH_INDEX,
            query_params=request.query_params,
        ).add(path=url_bits.split('/'))
        resp = requests.post(es_url, json=request.data)
        return Response(status=resp.status_code, data=resp.json(), headers={'Content-Type': 'application/vnd.api+json'})
