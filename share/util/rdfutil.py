import itertools

import rdflib
import rdflib.compare

from share import exceptions


DCT = rdflib.DCTERMS
DOI = rdflib.Namespace('https://doi.org/')
ORCID = rdflib.Namespace('https://orcid.org/')
OSF = rdflib.Namespace('https://osf.io/vocab/2022/')
OSFIO = rdflib.Namespace('https://osf.io/')
SHAREV2 = rdflib.Namespace('https://share.osf.io/vocab/2017/')


# namespace prefixes that should be safe to assume in all rdf graphs
# in this system, in addition to rdflib's 'core' (rdf, rdfs, owl...)
LOCAL_CONTEXT = {
    'dct': DCT,
    'doi': DOI,
    'orcid': ORCID,
    'osf': OSF,
    'osfio': OSFIO,
    'sharev2': SHAREV2,
}


def contextualized_graph():
    graph = rdflib.Graph()
    for prefix, namespace in LOCAL_CONTEXT.items():
        graph.bind(prefix, namespace)
    return graph


def checksum_urn(checksum_algorithm, checksum_hex):
    urn = f'urn:checksum/{checksum_algorithm}/{checksum_hex}'
    return rdflib.URIRef(urn)


PID_NAMESPACE_NORMALIZATION_MAP = {
    'http://osf.io/': OSFIO,
    'http://orcid.org/': ORCID,
    'http://doi.org/': DOI,
    'http://dx.doi.org/': DOI,
    'https://dx.doi.org/': DOI,
}


def normalize_pid_uri(pid_uri):
    if ':' not in pid_uri:
        raise exceptions.BadPid(f'does not look like a uri: {pid_uri}')
    pid_uri = pid_uri.strip()
    if '://' not in pid_uri:
        # is shortened form, 'prefix:term'
        (namespace_prefix, _, term) = pid_uri.partition(':')
        try:
            namespace = LOCAL_CONTEXT[namespace_prefix]
        except KeyError:
            raise exceptions.BadPid(f'unknown prefix "{namespace_prefix}" in shortened uri "{pid_uri}"')
        else:
            pid_uri = namespace[term]

    for abnormed_ns, normed_ns in PID_NAMESPACE_NORMALIZATION_MAP.items():
        if pid_uri.startswith(abnormed_ns):
            pid_uri = pid_uri.replace(abnormed_ns, normed_ns, 1)

    if pid_uri.startswith(OSFIO):
        # osf.io has inconsistent trailing-slash behavior
        pid_uri = pid_uri.rstrip('/')

    return rdflib.URIRef(pid_uri)


def pids_equal(uri_a, uri_b):
    return normalize_pid_uri(uri_a) == normalize_pid_uri(uri_b)


def graph_equals(actual_rdf_graph, expected_triples):
    expected_rdf_graph = rdflib.Graph()
    for triple in expected_triples:
        expected_rdf_graph.add(triple)
    return rdflib.compare.isomorphic(
        actual_rdf_graph,
        expected_rdf_graph,
    )


def connected_subgraph_triples(from_rdfgraph, focus, _already_focused=None):
    if _already_focused is None:
        _already_focused = set()
    elif focus in _already_focused:
        return
    _already_focused.add(focus)
    next_foci = set()
    for (subj, pred, obj) in from_rdfgraph.triples((focus, None, None)):
        yield (subj, pred, obj)
        if pred not in _already_focused:
            next_foci.add(pred)
        if obj not in _already_focused:
            next_foci.add(obj)
    for subj in from_rdfgraph.subjects(object=focus, unique=True):
        if subj not in _already_focused:
            next_foci.add(subj)
    for next_focus in next_foci:
        yield from connected_subgraph_triples(from_rdfgraph, next_focus, _already_focused)
