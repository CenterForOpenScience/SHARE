from __future__ import annotations
import datetime
import json
from typing import TYPE_CHECKING

from primitive_metadata import primitive_rdf as rdf

from trove import exceptions as trove_exceptions
from trove.vocab.namespaces import TROVE, RDF, OWL
from trove.vocab.osfmap import (
    OSFMAP_THESAURUS,
    osfmap_json_shorthand,
)
from ._base import IndexcardDeriver
if TYPE_CHECKING:
    from trove.util.json import JsonValue, JsonObject


class OsfmapJsonFullDeriver(IndexcardDeriver):
    # abstract method from IndexcardDeriver
    @staticmethod
    def deriver_iri() -> str:
        _iri = TROVE['derive/osfmap_json_full']
        assert isinstance(_iri, str)
        return _iri

    # abstract method from IndexcardDeriver
    @staticmethod
    def derived_datatype_iris() -> tuple[str]:
        return (RDF.JSON,)

    # abstract method from IndexcardDeriver
    def should_skip(self) -> bool:
        return False

    # abstract method from IndexcardDeriver
    def derive_card_as_text(self) -> str:
        return json.dumps(
            _RdfOsfmapJsonldRenderer().tripledict_as_nested_jsonld(
                self.data.tripledict,
                self.focus_iri,
            )
        )


class _RdfOsfmapJsonldRenderer:
    __nestvisiting_iris: set[str]

    def tripledict_as_nested_jsonld(self, tripledict: rdf.RdfTripleDictionary, focus_iri: str) -> JsonObject:
        self.__nestvisiting_iris = set()
        return self.__nested_rdfobject_as_jsonld(tripledict, focus_iri)

    def rdfobject_as_jsonld(self, rdfobject: rdf.RdfObject) -> JsonObject:
        if isinstance(rdfobject, frozenset):
            return self.twopledict_as_jsonld(
                rdf.twopledict_from_twopleset(rdfobject),
            )
        elif isinstance(rdfobject, rdf.Literal):
            if not rdfobject.datatype_iris or rdfobject.datatype_iris == {RDF.string}:
                return {'@value': rdfobject.unicode_value}
            if RDF.JSON in rdfobject.datatype_iris:
                # NOTE: does not reset jsonld context (is that a problem?)
                return json.loads(rdfobject.unicode_value)
            _language_tag = rdfobject.language
            if _language_tag:  # standard language tag
                return {
                    '@value': rdfobject.unicode_value,
                    '@language': _language_tag,
                }
            # datatype iri (or non-standard language iri)
            _datatype_iris = sorted(
                (
                    osfmap_json_shorthand().compact_iri(_datatype_iri)
                    for _datatype_iri in rdfobject.datatype_iris
                ),
                key=len,
            )
            return {
                '@value': rdfobject.unicode_value,
                '@type': (_datatype_iris if (len(_datatype_iris) > 1) else _datatype_iris[0]),
            }
        elif isinstance(rdfobject, str):
            return {'@id': osfmap_json_shorthand().compact_iri(rdfobject)}
        elif isinstance(rdfobject, (float, int)):
            return {'@value': rdfobject}
        elif isinstance(rdfobject, datetime.date):
            # just "YYYY-MM-DD"
            return {'@value': datetime.date.isoformat(rdfobject)}
        elif isinstance(rdfobject, tuple):
            return {'@list': [
                self.rdfobject_as_jsonld(_obj)
                for _obj in rdfobject
            ]}
        raise trove_exceptions.UnsupportedRdfObject(rdfobject)

    def twopledict_as_jsonld(self, twopledict: rdf.RdfTwopleDictionary) -> JsonObject:
        _jsonld = {}
        for _pred, _objectset in twopledict.items():
            if _objectset:
                _key = osfmap_json_shorthand().compact_iri(_pred)
                _jsonld[_key] = self._list_or_single_value(_pred, [
                    self.rdfobject_as_jsonld(_obj)
                    for _obj in _objectset
                ])
        return _jsonld

    def __nested_rdfobject_as_jsonld(
        self,
        tripledict: rdf.RdfTripleDictionary,
        rdfobject: rdf.RdfObject,
    ) -> JsonObject:
        _yes_nest = (
            isinstance(rdfobject, str)
            and (rdfobject not in self.__nestvisiting_iris)
            and (rdfobject in tripledict)
        )
        if not _yes_nest:
            return self.rdfobject_as_jsonld(rdfobject)
        self.__nestvisiting_iris.add(rdfobject)
        _nested_obj = (
            {}
            if rdfobject.startswith('_:')  # HACK: non-blank blank nodes (stop that)
            else {'@id': osfmap_json_shorthand().compact_iri(rdfobject)}
        )
        for _pred, _objectset in tripledict[rdfobject].items():
            _label = osfmap_json_shorthand().compact_iri(_pred)
            if _objectset:
                _nested_obj[_label] = self._list_or_single_value(
                    _pred,
                    [  # recursion:
                        self.__nested_rdfobject_as_jsonld(tripledict, _obj)
                        for _obj in _objectset
                    ],
                )
        self.__nestvisiting_iris.discard(rdfobject)
        return _nested_obj

    def _list_or_single_value(self, predicate_iri: str, json_list: list[JsonValue]) -> JsonValue:
        _only_one_object = OWL.FunctionalProperty in (
            OSFMAP_THESAURUS
            .get(predicate_iri, {})
            .get(RDF.type, ())
        )
        if _only_one_object:
            if len(json_list) > 1:
                raise trove_exceptions.OwlObjection((
                    f'expected at most one object for <{predicate_iri}>'
                    f' (got {json_list})'
                ))
            try:
                (_only_obj,) = json_list
            except ValueError:
                return None
            else:
                return _only_obj
        return (
            sorted(json_list, key=json.dumps)
            if len(json_list) > 1
            else json_list
        )
