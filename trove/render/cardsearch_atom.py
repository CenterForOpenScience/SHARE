from __future__ import annotations
import itertools
import typing

from django.utils.translation import gettext as _
from primitive_metadata import primitive_rdf as rdf

from trove.render.rendering import EntireRendering
from trove.util.datetime import datetime_isoformat_z
from trove.util.json import (
    json_strs,
    json_vals,
    json_datetimes,
)
from trove.util.xml import XmlBuilder
from trove.vocab import mediatypes
from trove.vocab.trove import trove_indexcard_namespace
from ._trovesearch_card_only import TrovesearchCardOnlyRenderer

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from trove.util.json import JsonObject
    from trove.render.rendering import ProtoRendering


class CardsearchAtomRenderer(TrovesearchCardOnlyRenderer):
    '''render card-search results into Atom following https://www.rfc-editor.org/rfc/rfc4287
    '''
    MEDIATYPE = mediatypes.ATOM

    def multicard_rendering(self, card_pages: Iterator[Sequence[tuple[str, JsonObject]]]) -> ProtoRendering:
        def _strs(*path: str) -> Iterator[str]:
            yield from json_strs(_osfmap_json, path, coerce_str=True)

        def _dates(*path: str) -> Iterator[str]:
            yield from map(datetime_isoformat_z, json_datetimes(_osfmap_json, path))

        _xb = XmlBuilder('feed', {'xmlns': 'http://www.w3.org/2005/Atom'})
        _xb.leaf('title', text=_('shtrove search results'))
        _xb.leaf('subtitle', text=_('feed of metadata records matching given filters'))
        _xb.leaf('link', text=self.response_focus.single_iri())
        _xb.leaf('id', text=self.response_focus.single_iri())
        for _card_iri, _osfmap_json in itertools.chain.from_iterable(card_pages):
            with _xb.nest('entry'):
                _iri = _osfmap_json.get('@id', _card_iri)
                _xb.leaf('link', {'href': _iri})
                _xb.leaf('id', text=self._atom_id(_card_iri))
                for _title in _strs('title'):
                    _xb.leaf('title', text=_title)
                for _desc in _strs('description'):
                    _xb.leaf('summary', text=_desc)
                for _keyword in _strs('keyword'):
                    _xb.leaf('category', text=_keyword)
                for _created in _dates('dateCreated'):
                    _xb.leaf('published', text=_created)
                for _creator_obj in json_vals(_osfmap_json, 'creator'):
                    assert isinstance(_creator_obj, dict)
                    with _xb.nest('author'):
                        for _name in json_strs(_creator_obj, ['name']):
                            _xb.leaf('name', text=_name)
                        _creator_iri = _creator_obj.get('@id')
                        if _creator_iri:
                            _xb.leaf('uri', text=_creator_iri)
                        for _sameas_iri in json_strs(_creator_obj, ['sameAs']):
                            _xb.leaf('uri', text=_sameas_iri)
        return EntireRendering(
            mediatype=self.MEDIATYPE,
            entire_content=bytes(_xb),
        )

    def _atom_id(self, card_iri: str) -> str:
        try:
            _uuid = rdf.iri_minus_namespace(card_iri, namespace=trove_indexcard_namespace())
        except ValueError:
            return card_iri
        return f'urn:uuid:{_uuid}'
