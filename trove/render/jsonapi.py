import base64
from collections import defaultdict
import contextlib
import dataclasses
import datetime
import itertools
import json
import time
from typing import Iterable, Union

from primitive_metadata import primitive_rdf

from trove import exceptions as trove_exceptions
from trove.vocab.jsonapi import (
    JSONAPI_MEMBERNAME,
    JSONAPI_RELATIONSHIP,
    JSONAPI_ATTRIBUTE,
    JSONAPI_LINK_OBJECT,
)
from trove.vocab import mediatypes
from trove.vocab.namespaces import (
    OSFMAP,
    OWL,
    RDF,
    TROVE,
    XSD,
)
from trove.vocab.trove import trove_indexcard_namespace
from ._base import BaseRenderer


# a jsonapi resource may pull rdf data using an iri or blank node
# (using conventions from py for rdf as python primitives)
_IriOrBlanknode = Union[str, frozenset]


def _resource_ids_defaultdict():
    _prefix = str(time.time_ns())
    _ints = itertools.count()

    def _iter_ids():
        while True:
            _id = next(_ints)
            yield f'{_prefix}-{_id}'

    _ids = _iter_ids()
    return defaultdict(lambda: next(_ids))


@dataclasses.dataclass
class RdfJsonapiRenderer(BaseRenderer):
    '''render rdf data into jsonapi resources, guided by a given rdf vocabulary

    the given vocab describes how rdf predicates and classes in the data should
    map to jsonapi fields and resource objects in the rendered output, using
    `prefix jsonapi: <https://jsonapi.org/format/1.1/#>` and linked anchors in
    the jsonapi spec to represent jsonapi concepts:
      - jsonapi member name:
          `<iri> jsonapi:document-member-names "foo"@en`
      - jsonapi attribute:
          `<predicate_iri> rdf:type jsonapi:document-resource-object-attributes`
      - jsonapi relationship:
          `<predicate_iri> rdf:type jsonapi:document-resource-object-relationships`
      - to-one relationship or single-value attribute:
          `<predicate_iri> rdf:type owl:FunctionalProperty`

    note: does not support relationship links (or many other jsonapi features)
    '''
    MEDIATYPE = mediatypes.JSONAPI
    INDEXCARD_DERIVER_IRI = TROVE['derive/osfmap_json']

    _identifier_object_cache: dict = dataclasses.field(default_factory=dict)
    _id_namespace_set: Iterable[primitive_rdf.IriNamespace] = (trove_indexcard_namespace(),)
    __to_include: set[primitive_rdf.RdfObject] | None = None
    __assigned_blanknode_resource_ids: defaultdict[frozenset, str] = dataclasses.field(
        default_factory=_resource_ids_defaultdict,
        repr=False,
    )

    def simple_render_document(self) -> str:
        return json.dumps(
            self.render_dict(self.response_focus.single_iri()),
            indent=2,  # TODO: pretty-print query param?
        )

    def render_dict(self, primary_iris: Union[str, Iterable[str]]) -> dict:
        _primary_data: dict | list | None = None
        _included_data = []
        with self._contained__to_include() as _to_include:
            if isinstance(primary_iris, str):
                _already_included = {primary_iris}
                _primary_data = self.render_resource_object(primary_iris)
            else:
                _already_included = set(primary_iris)
                _primary_data = [
                    self.render_resource_object(_iri)
                    for _iri in primary_iris
                ]
            while _to_include:
                _next = _to_include.pop()
                if _next not in _already_included:
                    _already_included.add(_next)
                    _included_data.append(self.render_resource_object(_next))
        _document = {'data': _primary_data}
        if _included_data:
            _document['included'] = _included_data
        return _document

    def render_resource_object(self, iri_or_blanknode: _IriOrBlanknode) -> dict:
        _resource_object = {**self.render_identifier_object(iri_or_blanknode)}
        _twopledict = (
            (self.response_data.tripledict.get(iri_or_blanknode) or {})
            if isinstance(iri_or_blanknode, str)
            else primitive_rdf.twopledict_from_twopleset(iri_or_blanknode)
        )
        for _pred, _obj_set in _twopledict.items():
            if _pred != RDF.type:
                self._render_field(_pred, _obj_set, into=_resource_object)
        if isinstance(iri_or_blanknode, str):
            _resource_object.setdefault('links', {})['self'] = iri_or_blanknode
        return _resource_object

    def render_identifier_object(self, iri_or_blanknode: _IriOrBlanknode):
        try:
            return self._identifier_object_cache[iri_or_blanknode]
        except KeyError:
            if isinstance(iri_or_blanknode, str):
                _type_iris = list(self.response_data.q(iri_or_blanknode, RDF.type))
                _id_obj = {
                    'id': self._resource_id_for_iri(iri_or_blanknode),
                }
                if _type_iris:
                    _id_obj['type'] = self._single_typename(_type_iris)
            elif isinstance(iri_or_blanknode, frozenset):
                _type_iris = [
                    _obj
                    for _pred, _obj in iri_or_blanknode
                    if _pred == RDF.type
                ]
                _id_obj = {
                    'id': self._resource_id_for_blanknode(iri_or_blanknode),
                    'type': self._single_typename(_type_iris),
                }
            else:
                raise trove_exceptions.ExpectedIriOrBlanknode(f'expected str or frozenset (got {iri_or_blanknode})')
            self._identifier_object_cache[iri_or_blanknode] = _id_obj
            return _id_obj

    def _single_typename(self, type_iris: list[str]):
        if not type_iris:
            return ''
        if len(type_iris) == 1:
            return self._membername_for_iri(type_iris[0])
        # choose one predictably, preferring osfmap and trove
        for _namespace in (OSFMAP, TROVE):
            _type_iris = sorted(_iri for _iri in type_iris if _iri in _namespace)
            if _type_iris:
                return self._membername_for_iri(_type_iris[0])
        return self._membername_for_iri(sorted(type_iris)[0])

    def _membername_for_iri(self, iri: str):
        try:
            _membername = next(self.thesaurus.q(iri, JSONAPI_MEMBERNAME))
        except StopIteration:
            pass
        else:
            if isinstance(_membername, primitive_rdf.Literal):
                return _membername.unicode_value
            raise trove_exceptions.ExpectedLiteralObject((iri, JSONAPI_MEMBERNAME, _membername))
        return self.iri_shorthand.compact_iri(iri)

    def _resource_id_for_blanknode(self, blanknode: frozenset, /):
        return self.__assigned_blanknode_resource_ids[blanknode]

    def _resource_id_for_iri(self, iri: str):
        for _iri_namespace in self._id_namespace_set:
            if iri in _iri_namespace:
                return primitive_rdf.iri_minus_namespace(iri, namespace=_iri_namespace)
        # check for a shorthand
        _compact = self.iri_shorthand.compact_iri(iri)
        if _compact != iri:
            return _compact
        # as fallback, encode the iri into a valid jsonapi member name
        return base64.urlsafe_b64encode(iri.encode()).decode()

    def _render_field(self, predicate_iri, object_set, *, into: dict):
        _is_relationship = (predicate_iri, RDF.type, JSONAPI_RELATIONSHIP) in self.thesaurus
        _is_attribute = (predicate_iri, RDF.type, JSONAPI_ATTRIBUTE) in self.thesaurus
        _field_key = self._membername_for_iri(predicate_iri)
        _doc_key = 'meta'  # unless configured for jsonapi, default to unstructured 'meta'
        if ':' not in _field_key:
            if _is_relationship:
                _doc_key = 'relationships'
            elif _is_attribute:
                _doc_key = 'attributes'
        if _is_relationship:
            _fieldvalue = self._render_relationship_object(predicate_iri, object_set)
        else:
            _fieldvalue = self._one_or_many(predicate_iri, self._attribute_datalist(object_set))
        # update the given `into` resource object
        into.setdefault(_doc_key, {})[_field_key] = _fieldvalue

    def _one_or_many(self, predicate_iri: str, datalist: list):
        _only_one = (predicate_iri, RDF.type, OWL.FunctionalProperty) in self.thesaurus
        if _only_one:
            if len(datalist) > 1:
                raise trove_exceptions.OwlObjection(f'multiple objects for to-one relation <{predicate_iri}>: {datalist}')
            return (datalist[0] if datalist else None)
        return datalist

    def _attribute_datalist(self, object_set):
        return [
            self._render_attribute_datum(_obj)
            for _obj in object_set
        ]

    def _render_relationship_object(self, predicate_iri, object_set):
        _data = []
        _links = {}
        for _obj in object_set:
            if isinstance(_obj, frozenset):
                if (RDF.type, RDF.Seq) in _obj:
                    for _seq_obj in primitive_rdf.sequence_objects_in_order(_obj):
                        _data.append(self.render_identifier_object(_seq_obj))
                        self._pls_include(_seq_obj)
                elif (RDF.type, JSONAPI_LINK_OBJECT) in _obj:
                    _key, _link_obj = self._render_link_object(_obj)
                    _links[_key] = _link_obj
                else:
                    _data.append(self.render_identifier_object(_obj))
                    self._pls_include(_obj)
            else:
                assert isinstance(_obj, str)
                _data.append(self.render_identifier_object(_obj))
                self._pls_include(_obj)
        _relationship_obj = {
            'data': self._one_or_many(predicate_iri, _data),
        }
        if _links:
            _relationship_obj['links'] = _links
        return _relationship_obj

    def _render_link_object(self, link_obj: frozenset):
        _membername = next(
            _obj.unicode_value
            for _pred, _obj in link_obj
            if _pred == JSONAPI_MEMBERNAME
        )
        _rendered_link = {
            'href': next(
                _obj
                for _pred, _obj in link_obj
                if _pred == RDF.value
            ),
            # TODO:
            # 'rel':
            # 'describedby':
            # 'title':
            # 'type':
            # 'hreflang':
            # 'meta':
        }
        return _membername, _rendered_link

    def _make_object_gen(self, object_set):
        for _obj in object_set:
            if isinstance(_obj, frozenset) and ((RDF.type, RDF.Seq) in _obj):
                yield from primitive_rdf.sequence_objects_in_order(_obj)
            else:
                yield _obj

    @contextlib.contextmanager
    def _contained__to_include(self):
        assert self.__to_include is None
        self.__to_include = set()
        try:
            yield self.__to_include
        finally:
            self.__to_include = None

    def _pls_include(self, item):
        if self.__to_include is not None:
            self.__to_include.add(item)

    def _render_attribute_datum(self, rdfobject: primitive_rdf.RdfObject) -> dict | list | str | float | int:
        if isinstance(rdfobject, frozenset):
            if (RDF.type, RDF.Seq) in rdfobject:
                return [
                    self._render_attribute_datum(_seq_obj)
                    for _seq_obj in primitive_rdf.sequence_objects_in_order(rdfobject)
                ]
            _json_blanknode = {}
            for _pred, _obj_set in primitive_rdf.twopledict_from_twopleset(rdfobject).items():
                _key = self._membername_for_iri(_pred)
                _json_blanknode[_key] = self._one_or_many(_pred, self._attribute_datalist(_obj_set))
            return _json_blanknode
        if isinstance(rdfobject, primitive_rdf.Literal):
            if RDF.JSON in rdfobject.datatype_iris:
                return json.loads(rdfobject.unicode_value)
            if XSD.integer in rdfobject.datatype_iris:
                return int(rdfobject.unicode_value)
            return rdfobject.unicode_value  # TODO: decide how to represent language
        elif isinstance(rdfobject, str):
            return self.render_identifier_object(rdfobject)
        elif isinstance(rdfobject, (float, int)):
            return rdfobject
        elif isinstance(rdfobject, datetime.date):
            # just "YYYY-MM-DD"
            return datetime.date.isoformat(rdfobject)
        raise trove_exceptions.UnsupportedRdfObject(rdfobject)
