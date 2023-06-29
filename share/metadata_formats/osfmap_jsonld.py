import datetime
import json
import typing

from gather import (
    focus,
    text,
    IANA_LANGUAGE,
    GatheringOrganizer,
)

from share.schema.osfmap import (
    osfmap_labeler,
    OSFMAP_NORMS,
    DCTERMS,
    FOAF,
    OSFMAP,
)
from share.search.rdf_as_jsonld import RdfAsJsonld
from share.util.rdfutil import SHAREv2
from share.util.graph import MutableGraph, MutableNode
from .base import MetadataFormatter


class OsfmapJsonldFormatter(MetadataFormatter):
    def format(self, normalized_data) -> typing.Optional[str]:
        _mgraph = MutableGraph.from_jsonld(normalized_data.data)
        _central_node = _mgraph.get_central_node(guess=True)
        _central_focus = _focus_for_mnode(_central_node)
        # TODO: move normd-to-rdf gathering elsewhere
        _gathering = osfmap_from_normd.new_gathering({
            'normd': normalized_data,
            'mnode': None,  # provided by focus
        })
        _gathering.ask_all_about(_central_focus)
        _tripledict = _gathering.leaf_a_record()
        _rdf_as_jsonld = RdfAsJsonld(
            OSFMAP_NORMS.vocabulary,
            osfmap_labeler,
        )
        _jsonld = _rdf_as_jsonld.tripledict_as_nested_jsonld(
            _tripledict,
            _central_focus.single_iri(),
        )
        return json.dumps(_jsonld)
