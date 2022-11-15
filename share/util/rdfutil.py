import rdflib
import rdflib.compare


DCT = rdflib.DCTERMS
OSF = rdflib.Namespace('https://osf.io/vocab/2022/')
OSFIO = rdflib.Namespace('https://osf.io/')


# in addition to rdflib's 'core' (rdf, rdfs, owl...)
OSF_CONTEXT = {
    'osf': OSF,
    'osfio': OSFIO,
    'dct': DCT,
}


# for parsing json:api
JSONAPI_CONTEXT = {
    'id': {'@type': '@id'},
    'data': '@graph',
    'attributes': '@nest',
    'relationships': '@nest',
}


OSFJSONAPI_CONTEXT = {
    **OSF_CONTEXT,
    **JSONAPI_CONTEXT,
}


def contextualized_graph():
    graph = rdflib.Graph()
    for prefix, namespace in OSF_CONTEXT.items():
        graph.bind(prefix, namespace)
    return graph


def checksum_urn(checksum_algorithm, checksum_hex):
    urn = f'urn:checksum/{checksum_algorithm}/{checksum_hex}'
    return rdflib.URIRef(urn)


def graph_equals(actual_rdf_graph, expected_triples):
    expected_rdf_graph = rdflib.Graph()
    for triple in expected_triples:
        expected_rdf_graph.add(triple)
    return rdflib.compare.isomorphic(
        actual_rdf_graph,
        expected_rdf_graph,
    )
