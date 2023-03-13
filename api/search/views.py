from django import http
from django.conf import settings

from rest_framework import views
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from api import authentication
from share.search import exceptions
from share.search.index_strategy import IndexStrategy


class Sharev2ElasticSearchView(views.APIView):
    """
    Elasticsearch endpoint for SHARE Data.
    """
    authentication_classes = (authentication.NonCSRFSessionAuthentication, )
    parser_classes = (JSONParser,)
    permission_classes = (AllowAny, )
    renderer_classes = (JSONRenderer, )

    def get(self, request):
        return self._handle_request(request)

    def post(self, request):
        return self._handle_request(request)

    def _handle_request(self, request):
        try:
            index_strategy = IndexStrategy.by_request(
                request=request,
                default_strategy=settings.DEFAULT_SHAREV2_INDEX_STRATEGY,
            )
        except exceptions.IndexStrategyError as error:
            raise http.Http404(str(error))
        queryparams = request.query_params.copy()
        queryparams.pop('indexStrategy', None)
        if 'scroll' in queryparams:
            return http.HttpResponseForbidden(reason='Scroll is not supported.')
        try:
            response = index_strategy.pls_handle_query__api_backcompat(
                request_body=request.data,
                request_queryparams=queryparams,
            )
            return Response(data=response, headers={'Content-Type': 'application/json'})
        except (exceptions.IndexStrategyError, NotImplementedError):
            return Response(status=418)  # TODO
