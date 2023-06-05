import logging

import gather
from django.http import JsonResponse
from django.views import View

from share.schema.osfmap import OSFMAP_VOCAB
from share.search.search_params import CardsearchParams
from share.search.trovesearch_gathering import (
    TROVE,
    TROVESEARCH_VOCAB,
    trovesearch_by_indexstrategy,
)
from share.search.rdf_as_jsonapi import RdfAsJsonapi


logger = logging.getLogger(__name__)


_TROVESEARCH_OSFMAP_VOCAB = {
    **TROVESEARCH_VOCAB,
    **OSFMAP_VOCAB,
}
if __debug__:
    if len(_TROVESEARCH_OSFMAP_VOCAB) != (len(TROVESEARCH_VOCAB) + len(OSFMAP_VOCAB)):
        _duplicate_keys = set(TROVESEARCH_VOCAB).intersection(OSFMAP_VOCAB)
        raise ValueError(f'vocab collision! duplicate keys: {_duplicate_keys}')


class CardsearchView(View):
    def get(self, request):
        _search_iri = request.build_absolute_uri()
        _search_gathering = trovesearch_by_indexstrategy.new_gathering({
            'search_params': CardsearchParams.from_querystring(
                request.META['QUERY_STRING'],
            ),
        })
        _search_gathering.ask(
            gather.focus(_search_iri, TROVE.Cardsearch),
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
        _as_jsonapi = RdfAsJsonapi(
            _search_gathering.leaf_a_record(),
            _TROVESEARCH_OSFMAP_VOCAB,
        )
        return JsonResponse(
            _as_jsonapi.jsonapi_datum_document(_search_iri),
            json_dumps_params={'indent': 2},
        )


class PropertysearchView(View):
    def get(self, request):
        raise NotImplementedError


class ValuesearchView(View):
    def get(self, request):
        raise NotImplementedError
