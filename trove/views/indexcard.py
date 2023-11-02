from django.views import View
from primitive_metadata import gather

from trove.render import render_response
from trove.trovesearch_gathering import trovesearch_by_indexstrategy
from trove.vocab.trove import TROVE, trove_indexcard_iri


class IndexcardView(View):
    def get(self, request, indexcard_uuid):
        _search_gathering = trovesearch_by_indexstrategy.new_gathering({
            # TODO (gather): allow omitting kwargs that go unused
            'search_params': None,
            'specific_index': None,
            'quoted_osfmap_json': not request.accepts('text/html'),  # TODO: consistent content negotiation
        })
        _indexcard_iri = trove_indexcard_iri(indexcard_uuid)
        _search_gathering.ask(
            {},  # TODO: build from `include`/`fields`
            focus=gather.focus(_indexcard_iri, TROVE.Indexcard),
        )
        _response_tripledict = _search_gathering.leaf_a_record()
        return render_response(request, _response_tripledict, _indexcard_iri)
