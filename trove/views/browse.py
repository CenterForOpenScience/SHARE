import dataclasses

from trove import exceptions as trove_exceptions
from trove.util.iris import unquote_iri
from trove.vocab import namespaces as _ns
from trove.vocab.osfmap import osfmap_json_shorthand
from trove.vocab.trove import trove_json_shorthand
from trove.trovebrowse_gathering import trovebrowse
from trove.util.trove_params import BasicTroveParams
from trove.util.queryparams import (
    QueryparamDict,
    get_single_value,
)
from ._base import GatheredTroveView


@dataclasses.dataclass(frozen=True)
class BrowseParams(BasicTroveParams):
    iri: str

    @classmethod
    def parse_queryparams(cls, queryparams: QueryparamDict) -> dict:
        _iri_value = get_single_value(queryparams, 'iri')
        if not _iri_value:
            raise trove_exceptions.MissingRequiredQueryParam('iri')
        return {
            **super().parse_queryparams(queryparams),
            'iri': cls._parse_iri(_iri_value),
        }

    @classmethod
    def _parse_iri(cls, iri_value: str):
        _iri = unquote_iri(iri_value)
        if ':' in _iri:
            return _ns.namespaces_shorthand().expand_iri(_iri)
        for _shorthand_factory in (osfmap_json_shorthand, trove_json_shorthand):
            _expanded = _shorthand_factory().expand_iri(_iri)
            if _expanded != _iri:
                return _expanded
        raise trove_exceptions.IriInvalid(_iri)

    @classmethod
    def _default_include(cls):
        return frozenset((
            _ns.TROVE.thesaurusEntry,
            _ns.FOAF.isPrimaryTopicOf,
            _ns.TROVE.usedAtPath,
        ))


class BrowseIriView(GatheredTroveView):
    gathering_organizer = trovebrowse
    params_type = BrowseParams

    def _get_focus_iri(self, request, params: BrowseParams):  # override GatheredTroveView
        return params.iri
