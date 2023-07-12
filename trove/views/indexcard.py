from django import http
from django.views import View
import gather

from share.search.rdf_as_jsonapi import RdfAsJsonapi
from trove.trovesearch_gathering import (
    trovesearch_by_indexstrategy,
)
from trove.vocab.trove import (
    TROVE,
    TROVE_VOCAB,
    TROVE_INDEXCARD,
    trove_labeler,
)


class IndexcardView(View):
    def get(self, request, indexcard_uuid):
        _search_gathering = trovesearch_by_indexstrategy.new_gathering({
            # TODO (gather.py): allow omitting kwargs that go unused
            'search_params': None,
            'specific_index': None,
        })
        _indexcard_iri = TROVE_INDEXCARD[str(indexcard_uuid)]
        _search_gathering.ask(
            gather.focus(_indexcard_iri, TROVE.Card),
            {},  # TODO: build from `include`/`fields`
        )
        _response_data = _search_gathering.leaf_a_record()
        _as_jsonapi = RdfAsJsonapi(
            data=_response_data,
            vocabulary=TROVE_VOCAB,
            labeler=trove_labeler,
            id_namespace=TROVE_INDEXCARD,
        )
        return http.JsonResponse(
            _as_jsonapi.jsonapi_datum_document(_indexcard_iri),
            json_dumps_params={'indent': 2},
        )
