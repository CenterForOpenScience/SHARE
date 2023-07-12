import typing

import gather

from share.search.rdf_as_jsonld import RdfAsJsonld
from share.util.checksum_iri import ChecksumIri
from share.util.rdfutil import IriLabeler
from trove.vocab.trove import (
    JSONAPI_MEMBERNAME,
    JSONAPI_RELATIONSHIP,
)

###
# rendering responses as jsonapi


# a jsonapi resource may pull rdf data using an iri or blank node
_ResourceKey = typing.Union[str, frozenset]


class RdfAsJsonapi:
    __to_include: set[_ResourceKey]
    __included: set[_ResourceKey]
    __twopledict_cache: dict[_ResourceKey, gather.RdfTwopleDictionary]
    __resource_id_cache: dict[_ResourceKey, str]
    __resource_type_cache: dict[_ResourceKey, str]

    def __init__(
        self,
        data: gather.RdfTripleDictionary,
        vocabulary: gather.RdfTripleDictionary,
        labeler: IriLabeler,
        id_namespace: typing.Optional[gather.IriNamespace] = None,
    ):
        self._vocabulary = vocabulary
        self._labeler = labeler
        self._tripledict = data
        self._as_jsonld = RdfAsJsonld(vocabulary, self._labeler)
        self._id_namespace = id_namespace
        self.__twopledict_cache = {}
        self.__resource_id_cache = {}
        self.__resource_type_cache = {}

    def jsonapi_error_document(self):
        raise NotImplementedError  # TODO

    def jsonapi_datum_document(self, primary_iri: str):
        self.__to_include = set()
        self.__included = {primary_iri}
        _primary_data = self.jsonapi_resource(primary_iri)
        _included = []
        while self.__to_include:
            _iri = self.__to_include.pop()
            if _iri not in self.__included:
                _included.append(self.jsonapi_resource(_iri))
        return {
            'data': _primary_data,
            'included': _included,  # TODO: support `include` queryparam
        }

    def jsonapi_resource(self, resource_key: _ResourceKey):
        _twopledict = self._resource_twopledict(resource_key)
        # split twopledict in two
        _attributes: gather.RdfTwopleDictionary = {}
        _relationships: gather.RdfTwopleDictionary = {}
        for _predicate, _obj_set in _twopledict.items():
            if self._is_relationship_iri(_predicate):
                _relationships[_predicate] = _obj_set
            elif _predicate != gather.RDF.type:
                _attributes[_predicate] = _obj_set
        _resource_obj = {
            'id': self._resource_id(resource_key),
            'type': self._resource_type(resource_key),
            'attributes': self._as_jsonld.twopledict_as_jsonld(_attributes),
            # TODO: links, meta?
        }
        _relationships_obj = self._jsonapi_relationships(_relationships)
        if _relationships_obj:
            _resource_obj['relationships'] = _relationships_obj
        return _resource_obj

    def _jsonapi_relationships(self, relationships: gather.RdfTwopleDictionary):
        _relationships = {}
        for _iri, _obj_set in relationships.items():
            _relation_types = self._vocabulary[_iri][gather.RDF.type]
            if gather.OWL.FunctionalProperty in _relation_types:
                if len(_obj_set) > 1:
                    raise ValueError(
                        f'multiple objects for to-one relation <{_iri}> (got {_obj_set})'
                    )
                _data = self._identifier_object(next(iter(_obj_set)))
            else:
                _data = [
                    self._identifier_object(_obj)
                    for _obj in _obj_set
                ]
            _relationships[self._labeler.get_label_or_iri(_iri)] = {'data': _data}
        return _relationships

    def _resource_twopledict(self, resource_key: _ResourceKey):
        try:
            return self.__twopledict_cache[resource_key]
        except KeyError:
            if isinstance(resource_key, str):
                _twopledict = self._tripledict.get(resource_key, {})
            elif isinstance(resource_key, frozenset):
                _twopledict = gather.twopleset_as_twopledict(resource_key)
            else:
                raise ValueError(f'expected str or frozenset (got {resource_key})')
            self.__twopledict_cache[resource_key] = _twopledict
            return _twopledict

    def _resource_id(self, resource_key: _ResourceKey):
        try:
            return self.__resource_id_cache[resource_key]
        except KeyError:
            if isinstance(resource_key, str):
                if self._id_namespace and resource_key in self._id_namespace:
                    _id = gather.IriNamespace.without_namespace(resource_key, namespace=self._id_namespace)
                else:
                    _checksum_iri = ChecksumIri.digest('sha-256', salt='iri', raw_data=resource_key)
                    _id = _checksum_iri.hexdigest
            elif isinstance(resource_key, frozenset):
                _twopledict = self._resource_twopledict(resource_key)
                _checksum_iri = ChecksumIri.digest_json(
                    'sha-256',
                    salt='blanknode',
                    raw_json=self._as_jsonld.twopledict_as_jsonld(_twopledict),
                )
                _id = _checksum_iri.hexdigest
            else:
                raise ValueError(f'expected str or frozenset (got {resource_key})')
            self.__resource_id_cache[resource_key] = _id
            return _id

    def _resource_type(self, resource_key: _ResourceKey):
        try:
            return self.__resource_type_cache[resource_key]
        except KeyError:
            _twopledict = self._resource_twopledict(resource_key)
            _type_iris = _twopledict.get(gather.RDF.type, ())
            if not _type_iris:
                raise ValueError(f'cannot find rdf:type for {resource_key}')
            for _type_iri in _type_iris:
                try:
                    _membername = self._labeler.get_label_or_iri(_type_iri)
                    break
                except ValueError:
                    continue
            else:  # for-loop did not `break`
                raise ValueError(
                    f'cannot find rdf:type for {resource_key} that'
                    f' itself has type <{JSONAPI_MEMBERNAME}> (found {_type_iris})'
                )
            self.__resource_type_cache[resource_key] = _membername
            return _membername

    def _identifier_object(self, resource_key: _ResourceKey):
        self.__to_include.add(resource_key)
        return {
            'id': self._resource_id(resource_key),
            'type': self._resource_type(resource_key),
        }

    def _is_relationship_iri(self, iri: str):
        try:
            return (
                JSONAPI_RELATIONSHIP
                in self._vocabulary[iri][gather.RDF.type]
            )
        except KeyError:
            return False
