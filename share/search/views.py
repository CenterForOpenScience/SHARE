import logging

import gather
from django.http import JsonResponse
from django.views import View

from share.search.search_params import CardsearchParams
from share.search.trovesearch_gathering import (
    TROVE,
    trovesearch,
)
from share.search.rdf_as_jsonapi import RdfAsJsonapi


logger = logging.getLogger(__name__)


class CardsearchView(View):
    def get(self, request):
        _search_iri = request.build_absolute_uri()
        _search_gathering = trovesearch.new_gathering({
            'search_params': CardsearchParams.from_querystring(
                request.META['QUERY_STRING'],
            ),
        })
        _search_gathering.ask(
            gather.Focus.new(_search_iri, TROVE.Cardsearch),
            {
                # TODO: build from jsonapi `include`/`fields` (with static defaults)
                TROVE.totalResultCount: None,
                TROVE.cardsearchText: None,
                TROVE.cardsearchFilter: None,
                TROVE.searchResult: {
                    TROVE.indexCard: {
                        TROVE.resourceMetadata,
                    },
                },
            },
        )
        _jsonapi = RdfAsJsonapi(_search_gathering).jsonapi_datum_document(_search_iri)
        return JsonResponse(_jsonapi)


class PropertysearchView(View):
    def get(self, request):
        raise NotImplementedError


class ValuesearchView(View):
    def get(self, request):
        raise NotImplementedError
