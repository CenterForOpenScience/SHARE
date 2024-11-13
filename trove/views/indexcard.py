from django.views import View
from primitive_metadata import gather

from trove import exceptions as trove_exceptions
from trove.render import get_renderer_type
from trove.trovesearch.trovesearch_gathering import trovesearch_by_indexstrategy
from trove.vocab.namespaces import TROVE
from trove.vocab.trove import trove_indexcard_iri
from ._responder import (
    make_http_error_response,
    make_http_response,
)


class IndexcardView(View):
    def get(self, request, indexcard_uuid):
        _renderer_type = get_renderer_type(request)
        try:
            _search_gathering = trovesearch_by_indexstrategy.new_gathering({
                # TODO (gather): allow omitting kwargs that go unused
                'search_params': None,
                'specific_index': None,
                'deriver_iri': _renderer_type.INDEXCARD_DERIVER_IRI,
            })
            _indexcard_iri = trove_indexcard_iri(indexcard_uuid)
            _search_gathering.ask(
                {},  # TODO: build from `include`/`fields`
                focus=gather.Focus.new(_indexcard_iri, TROVE.Indexcard),
            )
            _renderer = _renderer_type(_indexcard_iri, _search_gathering.leaf_a_record())
            return make_http_response(
                content_rendering=_renderer.render_document(),
                http_request=request,
            )
        except trove_exceptions.TroveError as _error:
            return make_http_error_response(
                error=_error,
                renderer=_renderer_type(_indexcard_iri),
            )
