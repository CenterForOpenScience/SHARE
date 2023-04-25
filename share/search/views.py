from django.http import JsonResponse
from django.views import View

from share.search.index_strategy import IndexStrategy
from share.search import search_params


class IndexCardSearchView(View):
    def get(self, request):
        search_index = IndexStrategy.get_for_searching(
            request.GET.get('indexStrategy'),
            with_default_fallback=True,
        )
        # TODO: get shaclbasket, render via content negotiation
        search_response_json = search_index.pls_handle_index_card_search(
            search_params.IndexCardSearchParams.from_querydicts((request.GET, request.POST))
        )
        return JsonResponse(search_response_json)


class IndexPropertySearchView(View):
    def get(self, request):
        raise NotImplementedError


class IndexValueSearchView(View):
    def get(self, request):
        raise NotImplementedError
