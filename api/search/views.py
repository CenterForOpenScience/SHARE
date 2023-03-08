from django import http

from rest_framework import views
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from api import authentication
from share.search import exceptions
from share.search.index_strategy import IndexStrategy


DEFAULT_INDEX_STRATEGY = 'sharev2_elastic5'  # TODO: switchable in admin


def _get_index_strategy(requested_index_strategy):
    if requested_index_strategy is None:
        index_strategy = IndexStrategy.by_name(DEFAULT_INDEX_STRATEGY)
    else:
        try:
            index_strategy = IndexStrategy.by_request(requested_index_strategy)
        except exceptions.IndexStrategyError as error:
            raise http.Http404(str(error))
    if not index_strategy.pls_check_exists():
        raise http.Http404(f'indexStrategy={requested_index_strategy} does not exist')
    return index_strategy


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
        queryparams = request.query_params.copy()
        if 'scroll' in queryparams:
            return http.HttpResponseForbidden(reason='Scroll is not supported.')
        requested_index_strategy = queryparams.pop('indexStrategy', [None])[0]
        index_strategy = _get_index_strategy(requested_index_strategy)
        try:
            response = index_strategy.pls_handle_query__api_backcompat(
                request_body=request.data,
                request_queryparams=queryparams,
            )
            return Response(data=response, headers={'Content-Type': 'application/json'})
        except (exceptions.IndexStrategyError, NotImplementedError):
            return Response(status=418)  # TODO
