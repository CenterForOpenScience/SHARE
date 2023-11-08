import datetime
import json

from primitive_metadata import primitive_rdf

from trove.util.iri_labeler import IriLabeler
from trove.vocab.namespaces import RDF, OWL


class RdfJsonldRenderer:  # TODO: inherit BaseRenderer, add to get_renderer
    def __init__(self, vocabulary: primitive_rdf.RdfTripleDictionary, labeler: IriLabeler):
        self.vocabulary = vocabulary
        self.labeler = labeler

    def render_document(self, data: primitive_rdf.RdfTripleDictionary, focus_iri: str) -> str:
        _rendered = self.tripledict_as_nested_jsonld(data, focus_iri)
        _rendered['@context'] = self.simple_jsonld_context()
        return json.dumps(_rendered, indent=2, sort_keys=True)

    def simple_jsonld_context(self):
        return self.labeler.all_iris_by_label()

    def tripledict_as_nested_jsonld(self, tripledict: primitive_rdf.RdfTripleDictionary, focus_iri: str):
        self.__nestvisiting_iris = set()
        return self.__nested_rdfobject_as_jsonld(tripledict, focus_iri)

    def rdfobject_as_jsonld(self, rdfobject: primitive_rdf.RdfObject) -> dict:
        if isinstance(rdfobject, frozenset):
            return self.twopledict_as_jsonld(
                primitive_rdf.twopledict_from_twopleset(rdfobject),
            )
        elif isinstance(rdfobject, primitive_rdf.Literal):
            if not rdfobject.datatype_iris:
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
            return {
                '@value': rdfobject.unicode_value,
                '@type': (
                    list(rdfobject.datatype_iris)
                    if len(rdfobject.datatype_iris) > 1
                    else next(iter(rdfobject.datatype_iris))
                ),
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
            if _objectset:
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
            and (rdfobject not in self.__nestvisiting_iris)
            and (rdfobject in tripledict)
        )
        if not _yes_nest:
            return self.rdfobject_as_jsonld(rdfobject)
        self.__nestvisiting_iris.add(rdfobject)
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
        self.__nestvisiting_iris.discard(rdfobject)
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
