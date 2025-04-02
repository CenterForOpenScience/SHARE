import dataclasses

from trove import exceptions as trove_exceptions
from trove.util.iris import unquote_iri
from trove.vocab.osfmap import osfmap_shorthand
from trove.vocab.trove import trove_shorthand
from trove.trovebrowse_gathering import trovebrowse
from trove.util.trove_params import BasicTroveParams
from trove.util.queryparams import (
    QueryparamDict,
    get_single_value,
    get_bool_value,
)
from ._base import BaseTroveView


@dataclasses.dataclass(frozen=True)
class BrowseParams(BasicTroveParams):
    iri: str
    blend_cards: bool

    @classmethod
    def parse_queryparams(cls, queryparams: QueryparamDict) -> dict:
        _iri_value = get_single_value(queryparams, 'iri')
        if not _iri_value:
            raise trove_exceptions.MissingRequiredQueryParam('iri')
        return {
            **super().parse_queryparams(queryparams),
            'iri': cls._parse_iri(_iri_value),
            'blend_cards': get_bool_value(queryparams, 'blendCards', if_absent=True),
        }

    @classmethod
    def _parse_iri(cls, iri_value: str):
        _iri = unquote_iri(iri_value)
        if ':' in _iri:
            _iri = trove_shorthand().expand_iri(_iri)
        else:  # NOTE: special osfmap
            _iri = osfmap_shorthand().expand_iri(_iri)
        return _iri


class BrowseIriView(BaseTroveView):
    gathering_organizer = trovebrowse
    params_type = BrowseParams

    def _get_focus_iri(self, request, params: BrowseParams):  # override BaseTroveView
        return params.iri

    def _get_gatherer_kwargs(self, params, renderer_type):  # override BaseTroveView
        return {
            **super()._get_gatherer_kwargs(params, renderer_type),
            'blend_cards': params.blend_cards,
        }
