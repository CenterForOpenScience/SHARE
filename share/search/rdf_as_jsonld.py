import datetime
import json

import gather

from share.util.rdfutil import IriLabeler


class RdfAsJsonld:
    def __init__(self, vocabulary: gather.RdfTripleDictionary, labeler: IriLabeler):
        self.vocabulary = vocabulary
        self.labeler = labeler

    def iri_to_shortlabel(self, iri: str):
        try:
            return self.labeler.get_label(iri)
        except KeyError:
            return iri

    def simple_jsonld_context(self):
        return self.labeler.all_iris_by_label()

    def rdfobject_as_jsonld(self, rdfobject: gather.RdfObject):
        if isinstance(rdfobject, frozenset):
            return self.twopledict_as_jsonld(
                gather.twopleset_as_twopledict(rdfobject),
            )
        elif isinstance(rdfobject, gather.Text):
            if not rdfobject.language_iris:
                return {'@value': rdfobject.unicode_text}
            if gather.RDF.JSON in rdfobject.language_iris:
                # NOTE: does not reset jsonld context
                return json.loads(rdfobject.unicode_text)
            try:  # TODO: preserve multiple language iris somehow
                _language_tag = next(
                    gather.IriNamespace.without_namespace(_iri, namespace=gather.IANA_LANGUAGE)
                    for _iri in rdfobject.language_iris
                    if _iri in gather.IANA_LANGUAGE
                )
            except StopIteration:  # got a non-standard language iri
                return {
                    '@value': rdfobject.unicode_text,
                    '@type': next(iter(rdfobject.language_iris)),
                }
            else:  # got a language tag
                return {
                    '@value': rdfobject.unicode_text,
                    '@language': _language_tag,
                }
        elif isinstance(rdfobject, str):
            return {'@id': self.iri_to_shortlabel(rdfobject)}
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

    def twopledict_as_jsonld(self, twopledict: gather.RdfTwopleDictionary) -> dict:
        _jsonld = {}
        for _pred, _objectset in twopledict.items():
            _key = self.iri_to_shortlabel(_pred)
            _jsonld[_key] = self._list_or_single_value(_pred, [
                self.rdfobject_as_jsonld(_obj)
                for _obj in _objectset
            ])
        return _jsonld

    def tripledict_as_nested_jsonld(self, tripledict: gather.RdfTripleDictionary, focus_iri: str):
        self.__nestvisited_iris = set()
        return self.__nested_rdfobject_as_jsonld(tripledict, focus_iri)

    def __nested_rdfobject_as_jsonld(
        self,
        tripledict: gather.RdfTripleDictionary,
        rdfobject: gather.RdfObject,
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
            _label = self.iri_to_shortlabel(_pred)
            _nested_obj[_label] = self._list_or_single_value(
                _pred,
                [  # recursion:
                    self.__nested_rdfobject_as_jsonld(tripledict, _obj)
                    for _obj in _objectset
                ],
            )
        return _nested_obj

    def _list_or_single_value(self, predicate_iri, objectset):
        _only_one_object = gather.OWL.FunctionalProperty in (
            self.vocabulary
            .get(predicate_iri, {})
            .get(gather.RDF.type, ())
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
