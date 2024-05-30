import json

from primitive_metadata import primitive_rdf as rdf

from trove.vocab.jsonapi import (
    JSONAPI_LINK_OBJECT,
    JSONAPI_MEMBERNAME,
)
from trove.vocab import mediatypes
from trove.vocab.namespaces import TROVE, RDF
from ._base import BaseRenderer


class TrovesearchSimpleJsonRenderer(BaseRenderer):
    '''for "simple json" search api -- very entangled with trove/trovesearch_gathering.py
    '''
    MEDIATYPE = mediatypes.JSON

    def render_document(self, data: rdf.RdfGraph, focus_iri: str) -> str:
        _focustypes = set(data.q(focus_iri, RDF.type))
        if TROVE.Cardsearch in _focustypes:
            _jsonable = self._render_cardsearch(data, focus_iri)
        elif TROVE.Valuesearch in _focustypes:
            _jsonable = self._render_valuesearch(data, focus_iri)
        elif TROVE.Indexcard in _focustypes:
            _jsonable = self._render_card(data, focus_iri)
        else:
            raise NotImplementedError(f'simplejson not implemented for any of {_focustypes}')
        # TODO: links, total in 'meta'
        return json.dumps({
            'data': _jsonable,
            'links': self._render_links(data, focus_iri),
            'meta': self._render_meta(data, focus_iri),
        }, indent=2)

    def _render_cardsearch(self, graph: rdf.RdfGraph, cardsearch_iri: str):
        return self._render_searchresultpage(graph, cardsearch_iri)

    def _render_valuesearch(self, graph: rdf.RdfGraph, valuesearch_iri: str):
        return self._render_searchresultpage(graph, valuesearch_iri)

    def _render_searchresultpage(self, graph: rdf.RdfGraph, focus_iri: str):
        # just each card's contents
        _results_sequence = next(
            _page
            for _page in graph.q(focus_iri, TROVE.searchResultPage)
            if rdf.is_container(_page)  # filter out page links
        )
        return [
            self._render_result(graph, _search_result_blanknode)
            for _search_result_blanknode in rdf.sequence_objects_in_order(_results_sequence)
        ]

    def _render_result(self, graph: rdf.RdfGraph, search_result_blanknode: rdf.RdfBlanknode):
        _card = next(
            _obj
            for _pred, _obj in search_result_blanknode
            if _pred == TROVE.indexCard
        )
        return self._render_card(graph, _card)

    def _render_card(self, graph: rdf.RdfGraph, card: str | rdf.RdfBlanknode):
        # just the card contents
        if isinstance(card, str):
            _card_contents = next(graph.q(card, TROVE.resourceMetadata))
        elif isinstance(card, frozenset):
            _card_contents = next(
                _obj
                for _pred, _obj in card
                if _pred == TROVE.resourceMetadata
            )
        else:
            raise NotImplementedError
        assert isinstance(_card_contents, rdf.Literal)
        assert RDF.JSON in _card_contents.datatype_iris
        _json_contents = json.loads(_card_contents.unicode_value)
        if isinstance(card, str):
            self._add_twople(_json_contents, 'foaf:primaryTopicOf', card)
        return _json_contents

    def _render_meta(self, graph: rdf.RdfGraph, focus_iri: str):
        _meta = {}
        try:
            _total = next(graph.q(focus_iri, TROVE.totalResultCount))
            if isinstance(_total, int):
                _meta['total'] = _total
            elif isinstance(_total, rdf.Literal):
                _meta['total'] = int(_total.unicode_value)
            elif _total == TROVE['ten-thousands-and-more']:
                _meta['total'] = 'trove:ten-thousands-and-more'
        except StopIteration:
            pass
        return _meta

    def _render_links(self, graph: rdf.RdfGraph, focus_iri: str):
        _links = {}
        for _pagelink in graph.q(focus_iri, TROVE.searchResultPage):
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
