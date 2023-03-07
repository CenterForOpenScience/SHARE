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


def _get_index_strategy_and_name(requested_index_name):
    if requested_index_name is None:
        default_strategy = IndexStrategy.by_name(DEFAULT_INDEX_STRATEGY)
        return default_strategy, default_strategy.alias_for_searching
    for index_strategy in IndexStrategy.for_all_indexes():
        if requested_index_name == index_strategy.name:
            return index_strategy, index_strategy.alias_for_searching
        if requested_index_name.startswith(index_strategy.current_index_prefix):
            requested_index_exists = (
                index_strategy
                .pls_check_exists(specific_index_name=requested_index_name)
            )
            if requested_index_exists:
                return index_strategy, requested_index_name
            else:
                raise http.Http404('unknown indexName')
    raise http.Http404('invalid indexName')


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
        requested_index_name = queryparams.pop('indexName', [None])[0]
        index_strategy, index_name = _get_index_strategy_and_name(requested_index_name)
        try:
            response = index_strategy.pls_handle_query__sharev2backcompat(
                request_body=request.body,
                request_queryparams=queryparams,
                specific_index_name=requested_index_name,
            )
            return Response(data=response, headers={'Content-Type': 'application/json'})
        except (exceptions.IndexStrategyError, NotImplementedError):
            return Response(status_code=418)  # TODO
