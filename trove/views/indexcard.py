from django import http
from django.views import View
import gather

from trove.render import render_from_rdf, JSONAPI_MEDIATYPE
from trove.trovesearch_gathering import trovesearch_by_indexstrategy
from trove.vocab.trove import TROVE, trove_indexcard_iri


class IndexcardView(View):
    def get(self, request, indexcard_uuid):
        _search_gathering = trovesearch_by_indexstrategy.new_gathering({
            # TODO (gather.py): allow omitting kwargs that go unused
            'search_params': None,
            'specific_index': None,
        })
        _indexcard_iri = trove_indexcard_iri(indexcard_uuid)
        _search_gathering.ask(
            gather.focus(_indexcard_iri, TROVE.Card),
            {},  # TODO: build from `include`/`fields`
        )
        _response_tripledict = _search_gathering.leaf_a_record()
        return http.HttpResponse(
            content=render_from_rdf(_response_tripledict, _indexcard_iri, JSONAPI_MEDIATYPE),
            content_type=JSONAPI_MEDIATYPE,
        )
