import logging

import gather
from django.http import JsonResponse
from django.views import View

from share.search.search_params import CardsearchParams
from share.search.trovesearch_gathering import (
    TROVE,
    TROVESEARCH,
)
from share.search.trovesearch_jsonapi import jsonapi_document


logger = logging.getLogger(__name__)


class CardsearchView(View):
    def get(self, request):
        _search_iri = request.build_absolute_uri()
        _search_gathering = gather.Gathering(
            norms=TROVESEARCH,
            search_params=CardsearchParams.from_querystring(request.META['QUERY_STRING']),
        )
        _search_gathering.ask(
            gather.Focus.new(_search_iri, TROVE.Cardsearch),
            {
                # TODO: build from jsonapi `include`/`fields` (with static defaults)
                TROVE.totalResultCount: {},
                TROVE.searchResult: {
                    TROVE.indexCard,
                },
            },
        )
        _leaft = _search_gathering.leaf_a_record()
        logger.critical(gather.tripledict_as_turtle(_leaft))
        _jsonapi = jsonapi_document(_search_iri, _leaft)
        return JsonResponse(_jsonapi)


class PropertysearchView(View):
    def get(self, request):
        raise NotImplementedError


class ValuesearchView(View):
    def get(self, request):
        raise NotImplementedError
