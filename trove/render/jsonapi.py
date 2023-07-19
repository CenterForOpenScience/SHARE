import hashlib
import json
from typing import Iterable, Union

from gather.primitive_rdf import (
    TripledictWrapper,
    RdfTripleDictionary,
    twopleset_as_twopledict,
    Text,
    IriNamespace,
)

from trove.render.jsonld import RdfJsonldRenderer
from trove.vocab.trove import (
    RDF,
    JSONAPI_MEMBERNAME,
    JSONAPI_RELATIONSHIP,
    JSONAPI_ATTRIBUTE,
    OWL,
)


# a jsonapi resource may pull rdf data using an iri or blank node
# (using conventions from py for rdf as python primitives)
_IriOrBlanknode = Union[str, frozenset]


class RdfJsonapiRenderer:
    def __init__(self, jsonapi_vocab: RdfTripleDictionary, data: RdfTripleDictionary):
        # given vocabulary expected to describe how to represent rdf data as
        # jsonapi resources (using prefix jsonapi: <https://jsonapi.org/format/1.1/#>)
        #   - jsonapi member name:
        #       `<iri> jsonapi:document-member-names "foo"@en`
        #   - jsonapi attribute:
        #       `<predicate_iri> rdf:type jsonapi:document-resource-object-attributes`
        #   - jsonapi relationship:
        #       `<predicate_iri> rdf:type jsonapi:document-resource-object-relationships`
        #   - to-one relationship or single-value attribute:
        #       `<predicate_iri> rdf:type owl:FunctionalProperty`
        self._vocab = TripledictWrapper(jsonapi_vocab)
        self._data = TripledictWrapper(data)
        self._identifier_object_cache = {}
        self._to_include = set()

    def jsonapi_error_document(self) -> dict:
        raise NotImplementedError  # TODO

    def render_data_document(self, primary_iris: Union[str, Iterable[str]]) -> dict:
        _document = {
            'data': None,
            'included': [],
        }
        self._to_include = set()
        _single_datum = isinstance(primary_iris, str)
        if _single_datum:
            _already_included = {primary_iris}
            _document['data'] = self.render_resource_object(primary_iris)
        else:
            _already_included = set(primary_iris)
            _document['data'] = [
                self.render_resource_object(_iri)
                for _iri in primary_iris
            ]
        while self._to_include:
            _next = self._to_include.pop()
            if _next not in _already_included:
                _already_included.add(_next)
                _document['included'].append(self.render_resource_object(_next))
        return _document

    def render_resource_object(self, iri_or_blanknode: _IriOrBlanknode) -> dict:
        # TODO: links, meta?
        _resource_object = {**self.render_identifier_object(iri_or_blanknode)}
        _twopledict = (
            (self._data.get(iri_or_blanknode) or {})
            if isinstance(iri_or_blanknode, str)
            else twopleset_as_twopledict(iri_or_blanknode)
        )
        for _pred, _obj_set in _twopledict.items():
            self._render_field(_pred, _obj_set, into=_resource_object)
        return _resource_object

    def render_identifier_object(self, iri_or_blanknode: _IriOrBlanknode):
        try:
            return self._identifier_object_cache[iri_or_blanknode]
        except KeyError:
            _id_obj = {}
            if isinstance(iri_or_blanknode, str):
                _id_obj['id'] = self._resource_id_for_iri(iri_or_blanknode)
                _id_obj['type'] = self._membername_for_types(
                    list(self._vocab.q(iri_or_blanknode, RDF.type)),
                )
            elif isinstance(iri_or_blanknode, frozenset):
                _id_obj['id'] = self._resource_id_for_blanknode(iri_or_blanknode)
                _id_obj['type'] = self._membername_for_types([
                    _obj
                    for _pred, _obj in iri_or_blanknode
                    if _pred == RDF.type
                ])
            else:
                raise ValueError(f'expected str or frozenset (got {iri_or_blanknode})')
            self._identifier_object_cache[iri_or_blanknode] = _id_obj
            return _id_obj

    def _membername_for_types(self, type_iris):
        for _type_iri in type_iris:
            try:
                _membername = next(self._vocab.q(_type_iri, JSONAPI_MEMBERNAME))
                assert isinstance(_membername, Text)
                return _membername.unicode_text
            except StopIteration:
                pass
        raise ValueError(f'could not find jsonapi type for {type_iris}')

    def _resource_twopledict(self, iri_or_blanknode: _IriOrBlanknode):
        try:
            return self.__twopledict_cache[iri_or_blanknode]
        except KeyError:
            if isinstance(iri_or_blanknode, str):
                _twopledict = self._data.get_twopledict(iri_or_blanknode)
            elif isinstance(iri_or_blanknode, frozenset):
                _twopledict = twopleset_as_twopledict(iri_or_blanknode)
            else:
                raise ValueError(f'expected str or frozenset (got {iri_or_blanknode})')
            self.__twopledict_cache[iri_or_blanknode] = _twopledict
            return _twopledict

    def _resource_id_for_blanknode(self, blanknode: frozenset):
        _blanknode_as_json = json.dumps(
            self._jsonld_renderer.twopledict_as_jsonld(self._resource_twopledict(blanknode)),
            sort_keys=True,
        )
        # content-addressed blanknode id
        return hashlib.sha256(_blanknode_as_json.encode()).hexdigest()

    def _resource_id_for_iri(self, iri: str):
        for _iri_namespace in self._id_namespace_set:
            if iri in _iri_namespace:
                return IriNamespace.without_namespace(iri, namespace=_iri_namespace)
        # hash the iri for a valid jsonapi member name
        return hashlib.sha256(iri.encode()).hexdigest()

    def _render_field(self, predicate_iri, object_set, *, into: dict):
        _field_types = set(self._vocab.q(predicate_iri, RDF.type))
        _is_relationship = (JSONAPI_RELATIONSHIP in _field_types)
        _is_attribute = (JSONAPI_ATTRIBUTE in _field_types)
        _doc_key = 'meta'  # unless configured for jsonapi, default to unstructured 'meta'
        try:
            _field_key = next(self._vocab.q(predicate_iri, JSONAPI_MEMBERNAME))
        except StopIteration:
            _field_key = predicate_iri  # use the full iri as key
        else:  # got a valid membername; may go in attributes or relationships
            if _is_relationship:
                _doc_key = 'relationships'
            elif _is_attribute:
                _doc_key = 'attributes'
        if _is_relationship:
            _data = self._relationship_valuelist(object_set)
            self._to_include.update(object_set)
        else:
            _data = self._attribute_valuelist(object_set)
        if OWL.FunctionalProperty in _field_types:
            if len(_data) > 1:
                raise ValueError(
                    f'multiple objects for to-one relation <{predicate_iri}> ({_data})'
                )
            try:
                _data = _data[0]
            except IndexError:
                _data = None
        into.setdefault(_doc_key, {})[_field_key] = (
            {'data': _data}
            if _is_relationship
            else _data
        )

    def _relationship_valuelist(self, object_set):
        return [
            self.render_identifier_object(_obj)
            for _obj in object_set
        ]

    def _attribute_valuelist(self, object_set):
        raise NotImplementedError('TODO')
