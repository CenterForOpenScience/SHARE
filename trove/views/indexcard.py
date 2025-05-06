from django.http import Http404

from trove import models as trove_db
from trove.trovesearch.search_params import IndexcardParams
from trove.trovesearch.trovesearch_gathering import (
    trovesearch_by_indexstrategy,
    IndexcardFocus,
)
from trove.vocab.trove import trove_indexcard_iri
from ._base import GatheredTroveView


class IndexcardView(GatheredTroveView):
    params_type = IndexcardParams
    gathering_organizer = trovesearch_by_indexstrategy

    def _build_focus(self, request, params, url_kwargs):
        try:
            _indexcard_uuid = url_kwargs['indexcard_uuid']
            return IndexcardFocus.new(
                iris=trove_indexcard_iri(_indexcard_uuid),
                indexcard=trove_db.Indexcard.objects.get(uuid=_indexcard_uuid),
            )
        except trove_db.Indexcard.DoesNotExist:
            raise Http404
