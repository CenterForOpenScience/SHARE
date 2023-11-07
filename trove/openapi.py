import itertools
import json
from typing import Iterable

from primitive_metadata import primitive_rdf

from trove.vocab.namespaces import TROVE, RDFS, RDF, DCTERMS
from trove.vocab.trove import TROVE_API_VOCAB


_OPENAPI_PARAM_LOCATION_BY_RDF_TYPE = {
    TROVE.QueryParameter: 'query',
    TROVE.PathParameter: 'path',
    TROVE.HeaderParameter: 'header',
    # TODO? 'cookie'
}


def get_trove_openapi_json() -> str:
    return json.dumps(get_trove_openapi(), indent=2)


def get_trove_openapi() -> dict:
    '''generate an openapi description of the trove api

    following https://spec.openapis.org/oas/v3.1.0
    '''
    # TODO: language parameter, get translations
    _api_graph = primitive_rdf.RdfGraph(TROVE_API_VOCAB)
    _path_iris = set(_api_graph.q(TROVE.API, TROVE.hasPath))
    _label = next(_api_graph.q(TROVE.API, RDFS.label))
    _comment = next(_api_graph.q(TROVE.API, RDFS.comment))
    _description = next(_api_graph.q(TROVE.API, DCTERMS.description))
    return {
        'openapi': '3.1.0',
        'info': {
            'title': _label.unicode_value,
            'summary': _comment.unicode_value,
            'description': _description.unicode_value,
            'termsOfService': 'https://github.com/CenterForOpenScience/cos.io/blob/HEAD/TERMS_OF_USE.md',
            'contact': {
                # 'name':
                # 'url': web-browsable version of this
                'email': 'share-support@osf.io',
            },
            # 'license':
            'version': '23.2.0',
        },
        'servers': [{
            'url': 'https://share.osf.io',
        }],
        'paths': dict(
            _openapi_path(_path_iri, _api_graph)
            for _path_iri in _path_iris
        ),
        'components': {
            'parameters': dict(_openapi_parameters(_path_iris, _api_graph)),
        },
    }


def _openapi_parameters(path_iris: Iterable[str], api_graph: primitive_rdf.RdfGraph):
    _param_iris = set(itertools.chain(*(
        api_graph.q(_path_iri, TROVE.hasParameter)
        for _path_iri in path_iris
    )))
    for _param_iri in _param_iris:
        # TODO: better error message on absence
        _label = next(api_graph.q(_param_iri, RDFS.label))
        _comment = next(api_graph.q(_param_iri, RDFS.comment))
        _description = next(api_graph.q(_param_iri, DCTERMS.description))
        _jsonschema = next(api_graph.q(_param_iri, TROVE.jsonSchema), None)
        _required = ((_param_iri, RDF.type, TROVE.RequiredParameter) in api_graph)
        _location = next(
            _OPENAPI_PARAM_LOCATION_BY_RDF_TYPE[_type_iri]
            for _type_iri in api_graph.q(_param_iri, RDF.type)
            if _type_iri in _OPENAPI_PARAM_LOCATION_BY_RDF_TYPE
        )
        yield _label.unicode_value, {
            'name': _label.unicode_value,
            'in': _location,
            'required': _required,
            'summary': _comment.unicode_value,
            'description': _description.unicode_value,
            'schema': (json.loads(_jsonschema.unicode_value) if _jsonschema else None),
        }


def _openapi_path(path_iri: str, api_graph: primitive_rdf.RdfGraph):
    # TODO: better error message on absence
    _iri_path = next(api_graph.q(path_iri, TROVE.iriPath))
    _label = next(api_graph.q(path_iri, RDFS.label), None)
    _description = next(api_graph.q(path_iri, DCTERMS.description), None)
    _param_labels = list(api_graph.q(path_iri, {TROVE.hasParameter: {RDFS.label}}))
    return _iri_path.unicode_value, {
        'get': {  # TODO (if generalizability): separate metadata by verb
            # 'tags':
            'summary': _label.unicode_value,
            'description': _description.unicode_value,
            # 'externalDocs':
            'operationId': path_iri,
            'parameters': [
                {'$ref': f'#/components/parameters/{_param_label.unicode_value}'}
                for _param_label in _param_labels
            ],
        },
    }
