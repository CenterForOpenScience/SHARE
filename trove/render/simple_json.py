import json

from primitive_metadata import primitive_rdf as rdf

from trove.vocab.jsonapi import (
    JSONAPI_LINK_OBJECT,
    JSONAPI_MEMBERNAME,
)
from trove.vocab import mediatypes
from trove.vocab.namespaces import TROVE, RDF
from ._simple import BaseSimpleCardRenderer


class TrovesearchSimpleJsonRenderer(BaseSimpleCardRenderer):
    '''for "simple json" search api -- very entangled with trove/trovesearch/trovesearch_gathering.py
    '''
    MEDIATYPE = mediatypes.JSON
    INDEXCARD_DERIVER_IRI = TROVE['derive/osfmap_json']

    def render_unicard_document(self, card_iri, card_content):
        return json.dumps({
            'data': self._render_card_content(card_iri, card_content),
            'links': self._render_links(),
            'meta': self._render_meta(),
        }, indent=2)

    def render_multicard_document(self, cards_iris_and_contents):
        return json.dumps({
            'data': [
                self._render_card_content(_card_iri, _card_content)
                for _card_iri, _card_content in cards_iris_and_contents
            ],
            'links': self._render_links(),
            'meta': self._render_meta(),
        }, indent=2)

    def _render_card_content(self, card_iri: str, card_content):
        assert isinstance(card_content, rdf.Literal)
        assert RDF.JSON in card_content.datatype_iris
        _json_contents = json.loads(card_content.unicode_value)
        self._add_twople(_json_contents, 'foaf:primaryTopicOf', card_iri)
        return _json_contents

    def _render_meta(self):
        _meta: dict[str, int | str] = {}
        try:
            _total = next(self.response_data.q(self.response_focus_iri, TROVE.totalResultCount))
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
        for _pagelink in self.response_data.q(self.response_focus_iri, TROVE.searchResultPage):
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
