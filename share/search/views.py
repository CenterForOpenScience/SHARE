from django.http import JsonResponse
from django.views import View

from share.search.index_strategy import IndexStrategy
from share.search import search_params


class CardsearchView(View):
    def get(self, request):
        search_index = IndexStrategy.get_for_searching(
            request.GET.get('indexStrategy'),
            with_default_fallback=True,
        )
        # TODO: get shaclbasket, render via content negotiation
        search_response_json = search_index.pls_handle_cardsearch(
            search_params.CardsearchParams.from_request(request)
        )
        return JsonResponse(search_response_json, safe=False)


class PropertysearchView(View):
    def get(self, request):
        raise NotImplementedError


class ValuesearchView(View):
    def get(self, request):
        raise NotImplementedError
