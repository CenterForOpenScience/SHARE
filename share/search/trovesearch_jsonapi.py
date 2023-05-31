import gather

from share.search.trovesearch_gathering import TROVE, TROVESEARCH


###
# rendering responses

def iri_to_labelword(iri: str):
    _twopledict = TROVESEARCH.vocabulary.get(iri, {})
    try:
        return next(
            _text.unicode_text
            for _text in _twopledict.get(gather.RDFS.label, ())
            if TROVE.word in _text.language_iris
        )
    except StopIteration:
        raise ValueError(f'could not find labelword for <{iri}>')


def _is_relationship_iri(iri: str):
    try:
        return (
            TROVE.Relationship
            in TROVESEARCH.vocabulary[iri][gather.RDF.type]
        )
    except KeyError:
        return False


def _iri_to_shortlabel():  # TODO: only once
    return {
        _iri: iri_to_labelword(_iri)
        for _iri in TROVESEARCH.vocabulary.keys()
    }


def jsonapi_resource(
    iri: str,
    resource_twopledict: gather.RdfTwopleDictionary,
):
    try:
        _type_iri = next(
            _iri
            for _iri in resource_twopledict[gather.RDF.type]
            if _iri in TROVESEARCH.focustype_iris
        )
    except (StopIteration, KeyError):
        raise ValueError(f'could not find type for <{iri}>')
    _attributes: gather.RdfTwopleDictionary = {}
    _relationships: gather.RdfTwopleDictionary = {}
    for _predicate, _objset in resource_twopledict.items():
        if _is_relationship_iri(_predicate):
            _relationships[_predicate] = _objset
        elif _predicate != gather.RDF.type:
            _attributes[_predicate] = _objset
    return {
        'type': iri_to_labelword(_type_iri),
        'attributes': gather.twopledict_as_jsonld(_attributes, TROVESEARCH.vocabulary, _iri_to_shortlabel()),
        'relationships': _jsonapi_relationships(_relationships),
    }


def jsonapi_document(
    primary_iri: str,
    response_tripledict: gather.RdfTripleDictionary,
):
    _primary_data = jsonapi_resource(primary_iri, response_tripledict[primary_iri])
    _included = (
        jsonapi_resource(_iri, _twopledict)
        for _iri, _twopledict in response_tripledict.items()
        if _iri != primary_iri
    )
    return {
        'data': _primary_data,
        'included': list(_included),
    }


def _jsonapi_relationships(relationships: gather.RdfTwopleDictionary):
    return {  # TODO: actual jsonapi
        iri_to_labelword(_rel_iri): {
            'data': [
                gather.rdfobject_as_jsonld(_obj, TROVESEARCH.vocabulary, _iri_to_shortlabel())
                for _obj in _obj_set
            ],
        }
        for _rel_iri, _obj_set in relationships.items()
    }
