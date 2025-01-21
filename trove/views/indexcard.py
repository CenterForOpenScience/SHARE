from django.views import View

from trove import exceptions as trove_exceptions
from trove import models as trove_db
from trove.render import (
    DEFAULT_RENDERER_TYPE,
    get_renderer_type,
)
from trove.trovesearch.search_params import IndexcardParams
from trove.trovesearch.trovesearch_gathering import (
    trovesearch_by_indexstrategy,
    IndexcardFocus,
)
from trove.vocab.trove import trove_indexcard_iri
from ._gather_ask import ask_gathering_from_params
from ._responder import (
    make_http_error_response,
    make_http_response,
)


class IndexcardView(View):
    def get(self, request, indexcard_uuid):
        try:
            _renderer_type = get_renderer_type(request)
            _gathering = trovesearch_by_indexstrategy.new_gathering({
                'deriver_iri': _renderer_type.INDEXCARD_DERIVER_IRI,
            })
            _indexcard_iri = trove_indexcard_iri(indexcard_uuid)
            _params = IndexcardParams.from_querystring(request.META['QUERY_STRING'])
            _focus = IndexcardFocus.new(
                iris=_indexcard_iri,
                indexcard=trove_db.Indexcard.objects.get_for_iri(_indexcard_iri),
            )
            ask_gathering_from_params(_gathering, _params, _focus)
            _renderer = _renderer_type(_focus, _gathering)
            return make_http_response(
                content_rendering=_renderer.render_document(),
                http_request=request,
            )
        except trove_exceptions.CannotRenderMediatype as _error:
            return make_http_error_response(
                error=_error,
                renderer_type=DEFAULT_RENDERER_TYPE,
            )
        except trove_exceptions.TroveError as _error:
            return make_http_error_response(
                error=_error,
                renderer_type=_renderer_type,
            )
