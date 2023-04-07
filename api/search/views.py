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
        queryparams = request.query_params.dict()
        requested_index_strategy = queryparams.pop('indexStrategy', None)
        if 'scroll' in queryparams:
            return http.HttpResponseForbidden(reason='Scroll is not supported.')
        try:
            specific_index = IndexStrategy.get_for_searching(
                requested_index_strategy,
                default_name=settings.DEFAULT_SHAREV2_INDEX_STRATEGY,
            )
        except exceptions.IndexStrategyError as error:
            raise http.Http404(str(error))
        try:
            response_json = specific_index.pls_handle_query__sharev2_backcompat(
                request_body=request.data,
                request_queryparams=queryparams,
            )
            return Response(data=response_json, headers={'Content-Type': 'application/json'})
        except (exceptions.IndexStrategyError, NotImplementedError) as error:
            return Response(status=418, data=str(error))  # TODO
