import requests

from furl import furl

from django import http
from django.conf import settings

from rest_framework import views
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from api import authentication


class ElasticSearch403View(views.APIView):
    """
    Elasticsearch endpoint for unsupported queries.
    """
    authentication_classes = (authentication.NonCSRFSessionAuthentication, )
    parser_classes = (JSONParser,)
    permission_classes = (AllowAny, )
    renderer_classes = (JSONRenderer, )

    def get(self, request, *args, **kwargs):
        return http.HttpResponseForbidden()

    def post(self, request, *args, **kwargs):
        return http.HttpResponseForbidden()


class ElasticSearchGetOnlyView(views.APIView):
    """
    Elasticsearch get only endpoint for SHARE Data.

    - _mappings
    """
    authentication_classes = (authentication.NonCSRFSessionAuthentication, )
    parser_classes = (JSONParser,)
    permission_classes = (AllowAny, )
    renderer_classes = (JSONRenderer, )

    def get(self, request, *args, url_bits='', **kwargs):
        params = request.query_params.copy()

        v = params.pop('v', None)
        index = settings.ELASTICSEARCH['PRIMARY_INDEX']
        if v:
            v = 'v{}'.format(v[0])
            if v not in settings.ELASTICSEARCH['INDEX_VERSIONS']:
                return http.HttpResponseBadRequest('Invalid search index version')
            index = '{}_{}'.format(index, v)
        es_url = furl(settings.ELASTICSEARCH['URL']).add(path=index, query_params=params).add(path=url_bits.split('/'))

        if request.method == 'GET':
            resp = requests.get(es_url)
        else:
            raise NotImplementedError()
        return Response(status=resp.status_code, data=resp.json(), headers={'Content-Type': 'application/vnd.api+json'})


class ElasticSearchPostOnlyView(views.APIView):
    """
    Elasticsearch post only endpoint for SHARE Data.

    - _suggest
    """
    authentication_classes = (authentication.NonCSRFSessionAuthentication, )
    parser_classes = (JSONParser,)
    permission_classes = (AllowAny, )
    renderer_classes = (JSONRenderer, )

    def post(self, request, *args, url_bits='', **kwargs):
        params = request.query_params.copy()

        v = params.pop('v', None)
        index = settings.ELASTICSEARCH['PRIMARY_INDEX']
        if v:
            v = 'v{}'.format(v[0])
            if v not in settings.ELASTICSEARCH['INDEX_VERSIONS']:
                return http.HttpResponseBadRequest('Invalid search index version')
            index = '{}_{}'.format(index, v)
        es_url = furl(settings.ELASTICSEARCH['URL']).add(path=index, query_params=params).add(path=url_bits.split('/'))

        if request.method == 'POST':
            resp = requests.post(es_url, json=request.data)
        else:
            raise NotImplementedError()
        return Response(status=resp.status_code, data=resp.json(), headers={'Content-Type': 'application/vnd.api+json'})


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

        if 'scroll' in params:
            return http.HttpResponseForbidden(reason='Scroll is not supported.')

        v = params.pop('v', None)
        index = settings.ELASTICSEARCH['PRIMARY_INDEX']
        if v:
            v = 'v{}'.format(v[0])
            if v not in settings.ELASTICSEARCH['INDEX_VERSIONS']:
                return http.HttpResponseBadRequest('Invalid search index version')
            index = '{}_{}'.format(index, v)
        es_url = furl(settings.ELASTICSEARCH['URL']).add(path=index, query_params=params).add(path=url_bits.split('/'))

        if request.method == 'GET':
            resp = requests.get(es_url)
        elif request.method == 'POST':
            resp = requests.post(es_url, json=request.data)
        else:
            raise NotImplementedError()
        return Response(status=resp.status_code, data=resp.json(), headers={'Content-Type': 'application/vnd.api+json'})
