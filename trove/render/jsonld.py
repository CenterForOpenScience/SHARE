import contextlib
import datetime
import json

from primitive_metadata import primitive_rdf as rdf

from trove.vocab.namespaces import RDF, OWL
from trove.vocab import mediatypes
from ._base import BaseRenderer


_PREDICATES_OF_FLEXIBLE_CARDINALITY = {
    # RDF.type,
    RDF.value,
}


class RdfJsonldRenderer(BaseRenderer):
    MEDIATYPE = mediatypes.JSONLD

    __visiting_iris: set | None = None

    def render_document(self, data: rdf.RdfGraph, focus_iri: str) -> str:
        return json.dumps(
            self.render_jsonld(data, focus_iri),
            indent=2,
            sort_keys=True,
        )

    def render_jsonld(
        self,
        rdfgraph: rdf.RdfGraph,
        focus_iri: str,
        with_context: bool = False,
    ) -> dict:
        with self.iri_shorthand.track_used_shorts() as _used_shorts:
            _rendered = self.rdfobject_as_jsonld(focus_iri, rdfgraph)
        if with_context:
            _rendered['@context'] = {
                _shorthand_name: self.iri_shorthand.expand_iri(_shorthand_name)
                for _shorthand_name in _used_shorts
            }
        return _rendered

    def literal_as_jsonld(self, rdfliteral: rdf.Literal):
        if not rdfliteral.datatype_iris or rdfliteral.datatype_iris == {RDF.string}:
            return {'@value': rdfliteral.unicode_value}
        if RDF.JSON in rdfliteral.datatype_iris:
            # NOTE: does not reset jsonld context (is that a problem?)
            return json.loads(rdfliteral.unicode_value)
        _language_tag = rdfliteral.language
        if _language_tag:  # standard language tag
            return {
                '@value': rdfliteral.unicode_value,
                '@language': _language_tag,
            }
        # datatype iri (or non-standard language iri)
        _datatype_iris = [
            self.iri_shorthand.compact_iri(_datatype_iri)
            for _datatype_iri in rdfliteral.datatype_iris
        ]
        return {
            '@value': rdfliteral.unicode_value,
            '@type': (
                _datatype_iris
                if len(_datatype_iris) != 1
                else _datatype_iris[0]
            ),
        }

    def rdfobject_as_jsonld(
        self,
        rdfobject: rdf.RdfObject,
        tripledict: rdf.RdfTripleDictionary | None = None,
    ):
        if isinstance(rdfobject, str):
            return self.iri_as_jsonld(rdfobject, tripledict)
        elif isinstance(rdfobject, frozenset):
            if (RDF.type, RDF.Seq) in rdfobject:
                # TODO: jsonld has lists but not sequences -- switch to lists?
                return {'@list': [
                    self.rdfobject_as_jsonld(_sequence_obj, tripledict)
                    for _sequence_obj in rdf.sequence_objects_in_order(rdfobject)
                ]}
            return self.blanknode_as_jsonld(rdfobject, tripledict)
        elif isinstance(rdfobject, rdf.Literal):
            return self.literal_as_jsonld(rdfobject)
        elif isinstance(rdfobject, (float, int, datetime.date)):
            return self.literal_as_jsonld(rdf.literal(rdfobject))
        raise ValueError(f'unrecognized RdfObject (got {rdfobject})')

    def blanknode_as_jsonld(
        self,
        blanknode: rdf.RdfBlanknode,
        tripledict: rdf.RdfTripleDictionary | None = None,
    ) -> dict:
        _twopledict = rdf.twopledict_from_twopleset(blanknode)
        _jsonld = {}
        for _pred, _objectset in _twopledict.items():
            if _objectset:
                _key = self.iri_shorthand.compact_iri(_pred)
                _jsonld[_key] = self._list_or_single_value(_pred, [
                    self.rdfobject_as_jsonld(_obj, tripledict)
                    for _obj in _objectset
                ])
        return _jsonld

    def iri_as_jsonld(
        self,
        iri: str,
        tripledict: rdf.RdfTripleDictionary | None = None,
    ):
        if (not tripledict) or (iri not in tripledict) or self.__already_visiting(iri):
            return self.iri_shorthand.compact_iri(iri)
        with self.__visiting(iri):
            _nested_obj = (
                {}
                if iri.startswith('_:')  # HACK: non-blank blank nodes (stop that)
                else {'@id': self.iri_shorthand.compact_iri(iri)}
            )
            for _pred, _objectset in tripledict[iri].items():
                if _objectset:
                    _nested_obj[self.iri_shorthand.compact_iri(_pred)] = self._list_or_single_value(
                        _pred,
                        [  # indirect recursion:
                            self.rdfobject_as_jsonld(_obj, tripledict)
                            for _obj in _objectset
                        ],
                    )
            return _nested_obj

    def _list_or_single_value(self, predicate_iri: str, objectlist: list):
        _only_one_object = (
            (predicate_iri, RDF.type, OWL.FunctionalProperty) in self.thesaurus
        )
        if _only_one_object:
            if len(objectlist) > 1:
                raise ValueError((
                    f'expected at most one object for <{predicate_iri}>'
                    f' (got {objectlist})'
                ))
            try:
                (_only_obj,) = objectlist
            except ValueError:
                return None
            else:
                return _only_obj
        if predicate_iri in _PREDICATES_OF_FLEXIBLE_CARDINALITY:
            return (
                objectlist
                if len(objectlist) != 1
                else objectlist[0]
            )
        return objectlist

    @contextlib.contextmanager
    def __visiting(self, iri: str):
        if self.__visiting_iris is None:
            self.__visiting_iris = set()
        self.__visiting_iris.add(iri)
        yield
        self.__visiting_iris.discard(iri)

    def __already_visiting(self, iri: str) -> bool:
        return bool(self.__visiting_iris and (iri in self.__visiting_iris))
