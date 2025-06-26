import itertools
import json
from typing import Iterable, Generator, Any, Tuple

from django.conf import settings
from primitive_metadata import primitive_rdf

from share.version import get_shtrove_version
from trove.util.randomness import shuffled
from trove.vocab import mediatypes
from trove.vocab.jsonapi import JSONAPI_MEMBERNAME
from trove.vocab.namespaces import TROVE, RDFS, RDF, DCTERMS
from trove.vocab.trove import TROVE_API_THESAURUS


_OPENAPI_PARAM_LOCATION_BY_RDF_TYPE = {
    TROVE.QueryParameter: 'query',
    TROVE.PathParameter: 'path',
    TROVE.HeaderParameter: 'header',
    # TODO? 'cookie'
}


def get_trove_openapi_json() -> str:
    return json.dumps(get_trove_openapi(), indent=2)


def get_trove_openapi() -> dict[str, Any]:
    '''generate an openapi description of the trove api

    following https://spec.openapis.org/oas/v3.1.0
    '''
    # TODO: language parameter, get translations
    _api_graph = primitive_rdf.RdfGraph(TROVE_API_THESAURUS)
    _path_iris = shuffled(set(_api_graph.q(TROVE.search_api, TROVE.hasPath)))
    _label = next(_api_graph.q(TROVE.search_api, RDFS.label))
    _comment = next(_api_graph.q(TROVE.search_api, RDFS.comment))
    return {
        'openapi': '3.1.0',
        # 'externalDocs': {'url': TROVE.search_api},
        'info': {
            'title': _label.unicode_value,
            'summary': _comment.unicode_value,
            'description': _markdown_description(TROVE.search_api, _api_graph),
            'termsOfService': 'https://github.com/CenterForOpenScience/cos.io/blob/HEAD/TERMS_OF_USE.md',
            'contact': {
                # 'name':
                # 'url': web-browsable version of this
                'email': 'share-support@osf.io',
            },
            # 'license':
            'version': get_shtrove_version(),
        },
        'servers': [{
            'url': settings.SHARE_WEB_URL,
        }],
        'paths': dict(
            _openapi_path(_path_iri, _api_graph)
            for _path_iri in _path_iris
        ),
        'components': {
            'parameters': dict(_openapi_parameters(_path_iris, _api_graph)),
            'examples': dict(_openapi_examples(_path_iris, _api_graph)),
        },
    }


def _openapi_parameters(path_iris: Iterable[str], api_graph: primitive_rdf.RdfGraph) -> Iterable[tuple[str, Any]]:
    _param_iris = set(itertools.chain(*(
        api_graph.q(_path_iri, TROVE.hasParameter)
        for _path_iri in path_iris
    )))
    for _param_iri in shuffled(_param_iris):
        # TODO: better error message on absence
        try:
            _jsonname = next(api_graph.q(_param_iri, JSONAPI_MEMBERNAME))
        except StopIteration:
            raise ValueError(f'no jsonapi membername for {_param_iri}')
        _label = next(api_graph.q(_param_iri, RDFS.label))
        _comment = next(api_graph.q(_param_iri, RDFS.comment))
        _jsonschema = next(api_graph.q(_param_iri, TROVE.jsonSchema), None)
        _required = ((_param_iri, RDF.type, TROVE.RequiredParameter) in api_graph)
        _location = next(
            _OPENAPI_PARAM_LOCATION_BY_RDF_TYPE[_type_iri]
            for _type_iri in api_graph.q(_param_iri, RDF.type)
            if _type_iri in _OPENAPI_PARAM_LOCATION_BY_RDF_TYPE
        )
        yield _jsonname.unicode_value, {
            'name': _label.unicode_value,
            'in': _location,
            'required': _required,
            'summary': _comment.unicode_value,
            'description': _markdown_description(_param_iri, api_graph),
            'schema': (json.loads(_jsonschema.unicode_value) if _jsonschema else None),
        }


def _openapi_examples(path_iris: Iterable[str], api_graph: primitive_rdf.RdfGraph) -> Iterable[tuple[str, Any]]:
    # assumes examples are blank nodes (frozenset of twoples)
    _examples = set(itertools.chain(*(
        api_graph.q(_path_iri, TROVE.example)
        for _path_iri in path_iris
    )))
    for _example_blanknode in _examples:
        _example = primitive_rdf.twopledict_from_twopleset(_example_blanknode)
        _label = ''.join(
            _literal.unicode_value
            for _literal in _example.get(RDFS.label, ())
        )
        _comment = ' '.join(
            _literal.unicode_value
            for _literal in _example.get(RDFS.comment, ())
        )
        _description = '\n\n'.join(
            _literal.unicode_value
            for _literal in _example.get(DCTERMS.description, ())
        )
        _value = next(iter(_example[RDF.value]))  # assume literal
        if RDF.JSON in _value.datatype_iris:
            _valuekey = 'value'  # literal json given
            _value = json.loads(_value.unicode_value)
        else:
            _valuekey = 'externalValue'  # link
            _value = _value.unicode_value
        yield _label, {
            'summary': _comment,
            'description': _description,
            _valuekey: _value,
        }


def _openapi_path(path_iri: str, api_graph: primitive_rdf.RdfGraph) -> Tuple[str, Any]:
    # TODO: better error message on absence
    try:
        _path = next(iter(_text(path_iri, TROVE.iriPath, api_graph)))
    except StopIteration:
        raise ValueError(f'could not find trove:iriPath for {path_iri}')
    _label = ' '.join(_text(path_iri, RDFS.label, api_graph))
    _param_labels = shuffled(_text(path_iri, {TROVE.hasParameter: {JSONAPI_MEMBERNAME}}, api_graph))
    _example_labels = shuffled(_text(path_iri, {TROVE.example: {RDFS.label}}, api_graph))
    return _path, {
        'get': {  # TODO (if generalizability): separate metadata by verb
            # 'tags':
            'summary': _label,
            'description': _markdown_description(path_iri, api_graph),
            # 'externalDocs':
            'operationId': path_iri,
            'parameters': [
                {'$ref': f'#/components/parameters/{_param_label}'}
                for _param_label in _param_labels
            ],
            'responses': {
                '200': {
                    'description': 'ok',
                    'content': {
                        mediatypes.JSONAPI: {
                            'examples': [
                                {'$ref': f'#/components/examples/{_example_label}'}
                                for _example_label in _example_labels
                            ],
                        },
                    },
                },
            },
        },
    }


def _concept_markdown_blocks(concept_iri: str, api_graph: primitive_rdf.RdfGraph) -> Generator[str, None, None]:
    for _label in api_graph.q(concept_iri, RDFS.label):
        yield f'## {_label.unicode_value}'
    for _comment in api_graph.q(concept_iri, RDFS.comment):
        yield f'<aside>{_comment.unicode_value}</aside>'
    for _desc in api_graph.q(concept_iri, DCTERMS.description):
        yield _desc.unicode_value


def _text(subj: Any, pred: Any, api_graph: primitive_rdf.RdfGraph) -> Iterable[str]:
    for _obj in api_graph.q(subj, pred):
        yield _obj.unicode_value


def _markdown_description(subj_iri: str, api_graph: primitive_rdf.RdfGraph) -> str:
    return '\n\n'.join((
        *(
            _description.unicode_value
            for _description in api_graph.q(subj_iri, DCTERMS.description)
        ),
        *(
            '\n\n'.join(_concept_markdown_blocks(_concept_iri, api_graph))
            for _concept_iri in api_graph.q(subj_iri, TROVE.usesConcept)
        ),
    ))
