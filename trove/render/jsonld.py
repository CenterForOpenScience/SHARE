import datetime
import json

from gather import primitive_rdf

from share.util.rdfutil import IriLabeler
from trove.vocab.namespaces import RDF, OWL


class RdfJsonldRenderer:
    def __init__(self, vocabulary: primitive_rdf.RdfTripleDictionary, labeler: IriLabeler):
        self.vocabulary = vocabulary
        self.labeler = labeler

    def simple_jsonld_context(self):
        return self.labeler.all_iris_by_label()

    def tripledict_as_nested_jsonld(self, tripledict: primitive_rdf.RdfTripleDictionary, focus_iri: str):
        self.__nestvisited_iris = set()
        return self.__nested_rdfobject_as_jsonld(tripledict, focus_iri)

    def rdfobject_as_jsonld(self, rdfobject: primitive_rdf.RdfObject) -> dict:
        if isinstance(rdfobject, frozenset):
            return self.twopledict_as_jsonld(
                primitive_rdf.twopleset_as_twopledict(rdfobject),
            )
        elif isinstance(rdfobject, primitive_rdf.Text):
            if not rdfobject.language_iri:
                return {'@value': rdfobject.unicode_text}
            if rdfobject.language_iri == RDF.JSON:
                # NOTE: does not reset jsonld context
                return json.loads(rdfobject.unicode_text)
            try:
                _language_tag = primitive_rdf.IriNamespace.without_namespace(
                    rdfobject.language_iri,
                    namespace=primitive_rdf.IANA_LANGUAGE,
                )
            except ValueError:  # non-standard language iri
                return {
                    '@value': rdfobject.unicode_text,
                    '@type': rdfobject.language_iri,
                }
            else:  # standard language tag
                return {
                    '@value': rdfobject.unicode_text,
                    '@language': _language_tag,
                }
        elif isinstance(rdfobject, str):
            return {'@id': self.labeler.get_label_or_iri(rdfobject)}
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
        raise ValueError(f'unrecognized RdfObject (got {rdfobject})')

    def twopledict_as_jsonld(self, twopledict: primitive_rdf.RdfTwopleDictionary) -> dict:
        _jsonld = {}
        for _pred, _objectset in twopledict.items():
            _key = self.labeler.get_label_or_iri(_pred)
            _jsonld[_key] = self._list_or_single_value(_pred, [
                self.rdfobject_as_jsonld(_obj)
                for _obj in _objectset
            ])
        return _jsonld

    def __nested_rdfobject_as_jsonld(
        self,
        tripledict: primitive_rdf.RdfTripleDictionary,
        rdfobject: primitive_rdf.RdfObject,
    ):
        _yes_nest = (
            isinstance(rdfobject, str)
            and (rdfobject not in self.__nestvisited_iris)
            and (rdfobject in tripledict)
        )
        if not _yes_nest:
            return self.rdfobject_as_jsonld(rdfobject)
        self.__nestvisited_iris.add(rdfobject)
        _nested_obj = (
            {}
            if rdfobject.startswith('_:')  # HACK: non-blank blank nodes (stop that)
            else {'@id': rdfobject}
        )
        for _pred, _objectset in tripledict[rdfobject].items():
            _label = self.labeler.get_label_or_iri(_pred)
            if _objectset:
                _nested_obj[_label] = self._list_or_single_value(
                    _pred,
                    [  # recursion:
                        self.__nested_rdfobject_as_jsonld(tripledict, _obj)
                        for _obj in _objectset
                    ],
                )
        return _nested_obj

    def _list_or_single_value(self, predicate_iri, objectset):
        _only_one_object = OWL.FunctionalProperty in (
            self.vocabulary
            .get(predicate_iri, {})
            .get(RDF.type, ())
        )
        if _only_one_object:
            if len(objectset) > 1:
                raise ValueError((
                    f'expected at most one object for <{predicate_iri}>'
                    f' (got {objectset})'
                ))
            try:
                (_only_obj,) = objectset
            except ValueError:
                return None
            else:
                return _only_obj
        return list(objectset)
