import rdflib
import rdflib.compare

from share import exceptions
from share.legacy_normalize.schema import ShareV2Schema


DCT = rdflib.DCTERMS
FOAF = rdflib.FOAF
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
    'foaf': FOAF,
    'orcid': ORCID,
    'osf': OSF,
    'osfio': OSFIO,
    'sharev2': SHAREV2,
}

KNOWN_PID_NAMESPACES = (
    DCT,
    DOI,
    FOAF,
    ORCID,
    OSF,
    OSFIO,
    SHAREV2,
    # TODO: exclude the following on prod?
    'https://staging.osf.io/',
    'https://staging2.osf.io/',
    'https://staging3.osf.io/',
    'https://test.osf.io/',
    'http://staging.osf.io/',
    'http://staging2.osf.io/',
    'http://staging3.osf.io/',
    'http://test.osf.io/',
)


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


def normalize_pid_uri(pid_uri, *, require_known_namespace=False):
    if (not pid_uri) or (':' not in pid_uri):
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

    if require_known_namespace:
        in_known_namespace = any(
            pid_uri.startswith(str(ns))
            for ns in KNOWN_PID_NAMESPACES
        )
        if not in_known_namespace:
            raise exceptions.BadPid(f'uri "{pid_uri}" is not in a known namespace (and `require_known_namespace` is set)')

    return rdflib.URIRef(pid_uri)


def pids_equal(uri_a, uri_b):
    try:
        return normalize_pid_uri(uri_a) == normalize_pid_uri(uri_b)
    except exceptions.BadPid:
        return False


def graph_equals(actual_rdf_graph, expected_triples):
    expected_rdf_graph = rdflib.Graph()
    for triple in expected_triples:
        expected_rdf_graph.add(triple)
    return rdflib.compare.isomorphic(
        actual_rdf_graph,
        expected_rdf_graph,
    )


def strip_namespace(uri, namespaces=None):
    if namespaces is None:
        namespaces = KNOWN_PID_NAMESPACES
    for namespace in namespaces:
        ns = str(namespace)
        if uri.startswith(ns):
            return uri[len(ns):]
    else:
        return None


def unwrapped_value(rdfgraph, focus_id, predicate_id, *, default=None):
    value = rdfgraph.value(focus_id, predicate_id)
    return (
        value.toPython()
        if value is not None
        else default
    )


def is_creativework(rdfgraph, maybe_work_id):
    type_id = rdfgraph.value(maybe_work_id, rdflib.RDF.type)
    if type_id:
        type_name = strip_namespace(type_id)
        if type_name:
            concrete_type = ShareV2Schema().get_type(type_name).concrete_type
            return concrete_type == 'abstractcreativework'
    return False


def get_related_agents(rdfgraph, focus, predicate_ids):
    related_list = [
        (predicate_id, related_id)
        for predicate_id in predicate_ids
        for related_id in rdfgraph.objects(focus, predicate_id)
    ]

    def sort_key(predicate_object):
        (predicate_id, related_id) = predicate_object
        return unwrapped_value(
            rdfgraph,
            related_id,
            SHAREV2.order_cited,
            default=99999,
        )
    return sorted(related_list, key=sort_key)


def get_related_agent_names(rdfgraph, focus, predicate_ids):
    return [
        get_related_agent_name(rdfgraph, related_id)
        for _, related_id in get_related_agents(rdfgraph, focus, predicate_ids)
    ]


def get_related_agent_name(rdfgraph, related_id):
    """get the name to refer to a related agent

    @param rdfgraph: rdflib.Graph instance
    @param related_id: related agent node in the graph (could be bnode, uriref, or literal)
    @returns string (possibly empty)
    """
    if isinstance(related_id, rdflib.Literal):
        agent_name = str(related_id)
    else:
        agent_name = rdfgraph.value(related_id, SHAREV2.cited_as)
        if not agent_name:
            agent_name = rdfgraph.value(related_id, SHAREV2.name)
            if not agent_name:
                name_parts = filter(None, [
                    rdfgraph.value(related_id, SHAREV2.given_name),
                    rdfgraph.value(related_id, SHAREV2.additional_name),
                    rdfgraph.value(related_id, SHAREV2.family_name),
                    rdfgraph.value(related_id, SHAREV2.suffix),
                ])
                agent_name = ' '.join(name_parts).strip()
    return agent_name


def connected_subgraph_triples(from_rdfgraph, focus, _already_focused=None):
    if _already_focused is None:
        _already_focused = set()
    elif focus in _already_focused:
        return
    _already_focused.add(focus)
    next_foci = set()
    for (subj, pred, obj) in from_rdfgraph.triples((focus, None, None)):
        yield (subj, pred, obj)
        next_foci.update({pred, obj} - _already_focused)
    for subj in from_rdfgraph.subjects(object=focus, unique=True):
        if subj not in _already_focused:
            next_foci.add(subj)
    for next_focus in next_foci:
        yield from connected_subgraph_triples(from_rdfgraph, next_focus, _already_focused)


class RdfBuilder:
    def __init__(self):
        self.rdfgraph = contextualized_graph()

    def add(self, subj, pred, obj):
        if obj is None:
            return  # is ok, just skip
        if not isinstance(subj, rdflib.term.Node):
            raise ValueError(f'subj should be rdflib-erated, got {subj}')
        if not isinstance(pred, rdflib.term.Node):
            raise ValueError(f'pred should be rdflib-erated, got {subj}')
        if not isinstance(obj, rdflib.term.Node):
            obj = rdflib.Literal(obj)
        self.rdfgraph.add((subj, pred, obj))
