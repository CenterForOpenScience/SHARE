from django.views import View
from primitive_metadata import gather

from trove import exceptions as trove_exceptions
from trove.render import get_renderer
from trove.trovesearch.trovesearch_gathering import trovesearch_by_indexstrategy
from trove.vocab.namespaces import TROVE
from trove.vocab.trove import trove_indexcard_iri


class IndexcardView(View):
    def get(self, request, indexcard_uuid):
        _renderer = get_renderer(request)
        try:
            _search_gathering = trovesearch_by_indexstrategy.new_gathering({
                # TODO (gather): allow omitting kwargs that go unused
                'search_params': None,
                'specific_index': None,
                'deriver_iri': _renderer.INDEXCARD_DERIVER_IRI,
            })
            _indexcard_iri = trove_indexcard_iri(indexcard_uuid)
            _search_gathering.ask(
                {},  # TODO: build from `include`/`fields`
                focus=gather.Focus.new(_indexcard_iri, TROVE.Indexcard),
            )
            _response_tripledict = _search_gathering.leaf_a_record()
            return _renderer.render_response(_response_tripledict, _indexcard_iri)
        except trove_exceptions.TroveError as _error:
            return _renderer.render_error_response(_error)
