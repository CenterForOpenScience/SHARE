import gather
from django.http import HttpResponse
from django.views import View

from share.search.trovesearch_gathering import (
    TROVE,
    TROVESEARCH,
)


class CardsearchView(View):
    def get(self, request):
        _search_iri = request.build_absolute_uri()
        _search_gathering = gather.Gathering(TROVESEARCH)
        _search_gathering.ask(
            gather.Focus.new(_search_iri, {TROVE.Cardsearch}),
            {
                # TODO: build from jsonapi `include`/`fields` (with static defaults)
                TROVE.totalResultCount: {},
                TROVE.searchResult: {
                    TROVE.indexCard,
                },
            },
        )
        _turt = gather.tripledict_as_turtle(
            _search_gathering.leaf_a_record(),
        )
        return HttpResponse(_turt)


class PropertysearchView(View):
    def get(self, request):
        raise NotImplementedError


class ValuesearchView(View):
    def get(self, request):
        raise NotImplementedError
