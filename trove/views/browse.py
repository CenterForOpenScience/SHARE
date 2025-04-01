import dataclasses

from trove import exceptions as trove_exceptions
from trove.util.iris import unquote_iri
from trove.vocab import namespaces as ns
from trove.trovebrowse_gathering import trovebrowse
from trove.util.trove_params import BasicTroveParams
from trove.util.queryparams import (
    QueryparamDict,
    get_single_value,
)
from ._base import BaseTroveView


@dataclasses.dataclass(frozen=True)
class BrowseParams(BasicTroveParams):
    iri: str
    with_amalgamation: bool

    @classmethod
    def parse_queryparams(cls, queryparams: QueryparamDict) -> dict:
        _iri_value = get_single_value(queryparams, 'iri')
        if not _iri_value:
            raise trove_exceptions.MissingRequiredQueryParam('iri')
        _iri = ns.NAMESPACES_SHORTHAND.expand_iri(unquote_iri(_iri_value))
        _iri = ns.NAMESPACES_SHORTHAND.expand_iri(unquote_iri(_iri_value))
        return {
            **super().parse_queryparams(queryparams),
            'iri': _iri,
            'with_amalgamation': ('withAmalgamation' in queryparams),
        }


class BrowseIriView(BaseTroveView):
    gathering_organizer = trovebrowse
    params_type = BrowseParams

    def _get_focus_iri(self, request, params: BrowseParams):  # override BaseTroveView
        return params.iri

    def _get_gatherer_kwargs(self, params, renderer_type):  # override BaseTroveView
        return {
            **super()._get_gatherer_kwargs(params, renderer_type),
            'with_amalgamation': params.with_amalgamation,
        }
