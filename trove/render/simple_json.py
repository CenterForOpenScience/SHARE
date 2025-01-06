import json
import re
import typing

from primitive_metadata import primitive_rdf as rdf

from trove.vocab.jsonapi import (
    JSONAPI_LINK_OBJECT,
    JSONAPI_MEMBERNAME,
)
from trove.vocab import mediatypes
from trove.vocab.namespaces import TROVE, RDF
from ._rendering import StreamableRendering
from ._simple_trovesearch import SimpleTrovesearchRenderer


class TrovesearchSimpleJsonRenderer(SimpleTrovesearchRenderer):
    '''for "simple json" search api -- very entangled with trove/trovesearch/trovesearch_gathering.py
    '''
    MEDIATYPE = mediatypes.JSON
    INDEXCARD_DERIVER_IRI = TROVE['derive/osfmap_json']

    def simple_unicard_rendering(self, card_iri, osfmap_json):
        return json.dumps({
            'data': self._render_card_content(card_iri, osfmap_json),
            'links': self._render_links(),
            'meta': self._render_meta(),
        }, indent=2)

    def multicard_rendering(self, card_pages: typing.Iterator[dict[str, dict]]):
        return StreamableRendering(
            mediatype=self.MEDIATYPE,
            content_stream=self._stream_json(card_pages),
        )

    def _stream_json(self, card_pages: typing.Iterator[dict[str, dict]]):
        _prefix = '{"data": ['
        yield _prefix
        _datum_prefix = None
        for _page in card_pages:
            for _card_iri, _osfmap_json in _page.items():
                if _datum_prefix is not None:
                    yield _datum_prefix
                yield json.dumps(self._render_card_content(_card_iri, _osfmap_json))
                _datum_prefix = ','
        _nondata = json.dumps({
            'meta': self._render_meta(),
            'links': self._render_links(),
        })
        yield re.sub(
            '^{',  # replace the opening {
            '],',  # ...with a closing ] for the "data" list
            _nondata,
            count=1,
        )

    def _render_card_content(self, card_iri: str, osfmap_json: dict):
        self._add_twople(osfmap_json, 'foaf:primaryTopicOf', card_iri)
        return osfmap_json

    def _render_meta(self):
        _meta: dict[str, int | str] = {}
        try:
            _total = next(self.response_gathering.ask(
                TROVE.totalResultCount,
                focus=self.response_focus,
            ))
            if isinstance(_total, int):
                _meta['total'] = _total
            elif isinstance(_total, rdf.Literal):
                _meta['total'] = int(_total.unicode_value)
            elif _total == TROVE['ten-thousands-and-more']:
                _meta['total'] = 'trove:ten-thousands-and-more'
        except StopIteration:
            pass
        return _meta

    def _render_links(self):
        _links = {}
        for _pagelink in self._page_links:
            _twopledict = rdf.twopledict_from_twopleset(_pagelink)
            if JSONAPI_LINK_OBJECT in _twopledict.get(RDF.type, ()):
                (_membername,) = _twopledict[JSONAPI_MEMBERNAME]
                (_link_url,) = _twopledict[RDF.value]
                _links[_membername.unicode_value] = _link_url
        return _links

    def _add_twople(self, json_dict, predicate_iri: str, object_iri: str):
        _obj_ref = {'@id': object_iri}
        _obj_list = json_dict.setdefault(predicate_iri, [])
        if isinstance(_obj_list, list):
            _obj_list.append(_obj_ref)
        else:
            json_dict[predicate_iri] = [_obj_list, _obj_ref]
