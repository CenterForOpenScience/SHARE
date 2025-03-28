import dataclasses

from trove import exceptions as trove_exceptions
from trove.util.iris import unquote_iri
from trove.vocab import namespaces as ns
from trove.trovebrowse_gathering import trovebrowse
from trove.util.base_trove_params import BaseTroveParams
from trove.util.queryparams import (
    QueryparamDict,
    QueryparamName,
    get_single_value,
)
from ._base import BaseTroveView


@dataclasses.dataclass(frozen=True)
class BrowseParams(BaseTroveParams):
    iri: str

    @classmethod
    def parse_queryparams(cls, queryparams: QueryparamDict) -> dict:
        _iri_value = get_single_value(queryparams, QueryparamName('iri'))
        if not _iri_value:
            raise trove_exceptions.MissingRequiredQueryParam('iri')
        _iri = ns.NAMESPACES_SHORTHAND.expand_iri(unquote_iri(_iri_value))
        return {
            **super().parse_queryparams(queryparams),
            'iri': _iri,
        }


class BrowseIriView(BaseTroveView):
    gathering_organizer = trovebrowse
    params_type = BrowseParams

    def _get_focus_iri(self, request, params: BrowseParams):
        return params.iri
