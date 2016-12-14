import requests
from rest_framework import views
from django import http
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

    - [Creative Works](/api/v2/search/creativeworks/_search) - Search individual documents harvested
    - [Agents](/api/v2/search/agents/_search) - Search agents from havested documents
    - [Tags](/api/v2/search/tags/_search) - Tags placed on documents
    - [Sources](/api/v2/search/sources/_search) - Data sources
    """
    authentication_classes = (authentication.NonCSRFSessionAuthentication, )
    parser_classes = (JSONParser,)
    permission_classes = (AllowAny, )
    renderer_classes = (JSONRenderer, )

    def get(self, request, *args, url_bits='', **kwargs):
        return self._handle_request(request, url_bits)

    def post(self, request, *args, url_bits='', **kwargs):
        return self._handle_request(request, url_bits)

    def _handle_request(self, request, url_bits):
        params = request.query_params.copy()
        v = params.pop('v', None)
        index = settings.ELASTICSEARCH_INDEX
        if v:
            v = 'v{}'.format(v[0])
            if v not in settings.ELASTICSEARCH_INDEX_VERSIONS:
                return http.HttpResponseBadRequest('Invalid search index version')
            index = '{}_{}'.format(index, v)
        es_url = furl(settings.ELASTICSEARCH_URL).add(path=index, query_params=params).add(path=url_bits.split('/'))

        if request.method == 'GET':
            resp = requests.get(es_url)
        elif request.method == 'POST':
            resp = requests.post(es_url, json=request.data)
        else:
            raise NotImplementedError()
        return Response(status=resp.status_code, data=resp.json(), headers={'Content-Type': 'application/vnd.api+json'})
