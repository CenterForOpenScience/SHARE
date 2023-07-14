import hashlib
import typing

import gather

from share.util.rdfutil import IriLabeler
from trove.render.jsonld import RdfAsJsonld
from trove.vocab.trove import (
    JSONAPI_MEMBERNAME,
    JSONAPI_RELATIONSHIP,
)


# a jsonapi resource may pull rdf data using an iri or blank node
# (using conventions from gather.py for rdf as python primitives)
_IriOrBlanknode = typing.Union[str, frozenset]


class RdfJsonapiRenderer:
    __to_include: set[_IriOrBlanknode]
    __included: set[_IriOrBlanknode]
    __twopledict_cache: dict[_IriOrBlanknode, gather.RdfTwopleDictionary]
    __resource_id_cache: dict[_IriOrBlanknode, str]
    __resource_type_cache: dict[_IriOrBlanknode, str]

    def __init__(
        self,
        data: gather.RdfTripleDictionary,
        vocabulary: gather.RdfTripleDictionary,
        labeler: IriLabeler,
    ):
        # given vocabulary expected to describe how predicates are represented in jsonapi:
        #   - jsonapi member name:
        #       `<predicate_iri> jsonapi:document-member-names "foo"@en`
        #   - jsonapi attribute:
        #       `<predicate_iri> rdf:type jsonapi:document-resource-object-attributes`
        #   - jsonapi relationship:
        #       `<predicate_iri> rdf:type jsonapi:document-resource-object-relationships`
        #   - to-one relationship or single-value attribute:
        #       `<predicate_iri> rdf:type owl:FunctionalProperty`
        self._vocabulary = vocabulary
        self._labeler = labeler
        self._tripledict = data
        self._jsonld_renderer = RdfAsJsonld(vocabulary, self._labeler)
        self.__twopledict_cache = {}
        self.__resource_id_cache = {}
        self.__resource_type_cache = {}

    def jsonapi_error_document(self) -> dict:
        raise NotImplementedError  # TODO

    def jsonapi_datum_document(self, primary_iri: str) -> dict:
        self.__to_include = set()
        self.__included = {primary_iri}
        _primary_data = self.jsonapi_resource_object(primary_iri)
        _included = []
        while self.__to_include:
            _iri = self.__to_include.pop()
            if _iri not in self.__included:
                _included.append(self.jsonapi_resource_object(_iri))
        return {
            'data': _primary_data,
            'included': _included,  # TODO: support `include` queryparam
        }

    def jsonapi_resource_object(self, iri_or_blanknode: _IriOrBlanknode) -> dict:
        _twopledict = self._resource_twopledict(iri_or_blanknode)
        # split twopledict in two
        _attributes: gather.RdfTwopleDictionary = {}
        _relationships: gather.RdfTwopleDictionary = {}
        for _predicate, _obj_set in _twopledict.items():
            if self._is_relationship_iri(_predicate):
                _relationships[_predicate] = _obj_set
            elif _predicate != gather.RDF.type:
                _attributes[_predicate] = _obj_set
        _resource_obj = {
            'id': self._resource_id(iri_or_blanknode),
            'type': self._resource_type(iri_or_blanknode),
            'attributes': self._jsonld_renderer.twopledict_as_jsonld(_attributes),
            # TODO: links, meta?
        }
        _relationships_obj = self._render_jsonapi_relationships(_relationships)
        if _relationships_obj:
            _resource_obj['relationships'] = _relationships_obj
        return _resource_obj

    def jsonapi_resource_id(self, iri_or_blanknode: _IriOrBlanknode):
        try:
            return self.__resource_id_cache[iri_or_blanknode]
        except KeyError:
            if isinstance(iri_or_blanknode, str):
                _id = self._make_resource_id_for_iri(iri_or_blanknode)
            elif isinstance(iri_or_blanknode, frozenset):
                _id = self._make_resource_id_for_blanknode(iri_or_blanknode)
            else:
                raise ValueError(f'expected str or frozenset (got {iri_or_blanknode})')
            self.__resource_id_cache[iri_or_blanknode] = _id
            return _id

    def jsonapi_resource_type(self, iri_or_blanknode: _IriOrBlanknode):
        try:
            return self.__resource_type_cache[iri_or_blanknode]
        except KeyError:
            _twopledict = self._resource_twopledict(iri_or_blanknode)
            _type_iris = _twopledict.get(gather.RDF.type, ())
            if not _type_iris:
                raise ValueError(f'cannot find rdf:type for {iri_or_blanknode}')
            for _type_iri in _type_iris:
                try:
                    _membername = self._labeler.get_label_or_iri(_type_iri)
                    break
                except ValueError:
                    continue
            else:  # for-loop did not `break`
                raise ValueError(
                    f'cannot find rdf:type for {iri_or_blanknode} that'
                    f' itself has type <{JSONAPI_MEMBERNAME}> (found {_type_iris})'
                )
            self.__resource_type_cache[iri_or_blanknode] = _membername
            return _membername

    def _resource_twopledict(self, iri_or_blanknode: _IriOrBlanknode):
        try:
            return self.__twopledict_cache[iri_or_blanknode]
        except KeyError:
            if isinstance(iri_or_blanknode, str):
                _twopledict = self._tripledict.get(iri_or_blanknode, {})
            elif isinstance(iri_or_blanknode, frozenset):
                _twopledict = gather.twopleset_as_twopledict(iri_or_blanknode)
            else:
                raise ValueError(f'expected str or frozenset (got {iri_or_blanknode})')
            self.__twopledict_cache[iri_or_blanknode] = _twopledict
            return _twopledict

    def _make_resource_id_for_blanknode(self, blanknode: frozenset):
        _blanknode_as_json = self._jsonld_renderer.twopledict_as_jsonld(
            self._resource_twopledict(blanknode)
        )
        # content-addressed blanknode id
        return hashlib.sha256(_blanknode_as_json.encode()).hexdigest()

    def _make_resource_id_for_iri(self, iri: str):
        for _iri_namespace in self.id_namespace_set:
            if iri in _iri_namespace:
                return gather.IriNamespace.without_namespace(iri, namespace=_iri_namespace)
        # hash the iri for a valid jsonapi member name
        return hashlib.sha256(iri.encode()).hexdigest()

    def _render_jsonapi_relationships(self, relationships: gather.RdfTwopleDictionary):
        _relationships = {}
        for _iri, _obj_set in relationships.items():
            _relation_types = self._vocabulary[_iri][gather.RDF.type]
            if gather.OWL.FunctionalProperty in _relation_types:
                if len(_obj_set) > 1:
                    raise ValueError(
                        f'multiple objects for to-one relation <{_iri}> (got {_obj_set})'
                    )
                _data = self._render_identifier_object(next(iter(_obj_set)))
            else:
                _data = [
                    self._render_identifier_object(_obj)
                    for _obj in _obj_set
                ]
            _relationships[self._labeler.get_label_or_iri(_iri)] = {'data': _data}
        return _relationships

    def _render_identifier_object(self, iri_or_blanknode: _IriOrBlanknode):
        self.__to_include.add(iri_or_blanknode)
        return {
            'id': self.jsonapi_resource_id(iri_or_blanknode),
            'type': self.jsonapi_resource_type(iri_or_blanknode),
        }

    def _is_relationship_iri(self, iri: str):
        try:
            return (
                JSONAPI_RELATIONSHIP
                in self._vocabulary[iri][gather.RDF.type]
            )
        except KeyError:
            return False
