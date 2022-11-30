import rdflib
import rdflib.compare

from share.legacy_normalize.schema import ShareV2Schema
from share.util.graph import MutableGraph


DCT = rdflib.DCTERMS
SHAREV2 = rdflib.Namespace('https://share.osf.io/vocab/2017/')
OSF = rdflib.Namespace('https://osf.io/vocab/2022/')
OSFIO = rdflib.Namespace('https://osf.io/')
DOI = rdflib.Namespace('https://doi.org/')
DXDOI = rdflib.Namespace('https://dx.doi.org/')


# in addition to rdflib's 'core' (rdf, rdfs, owl...)
LOCAL_CONTEXT = {
    'osf': OSF,
    'osfio': OSFIO,
    'dct': DCT,
    'sharev2': SHAREV2,
    'doi': DOI,
}


def contextualized_graph():
    graph = rdflib.Graph()
    for prefix, namespace in LOCAL_CONTEXT.items():
        graph.bind(prefix, namespace)
    return graph


def checksum_urn(checksum_algorithm, checksum_hex):
    urn = f'urn:checksum/{checksum_algorithm}/{checksum_hex}'
    return rdflib.URIRef(urn)


def normalize_pid_uri(pid_uri):
    if ':' not in pid_uri:
        raise ValueError(f'does not look like a URI: {pid_uri}')
    pid_uri = pid_uri.strip()
    if '://' not in pid_uri:
        # is shortened form, 'prefix:term'
        (namespace_prefix, _, term) = pid_uri.partition(':')
        try:
            namespace = LOCAL_CONTEXT[namespace_prefix]
        except KeyError:
            raise ValueError(f'unknown uri prefix "{namespace_prefix}" from uri "{pid_uri}"')
        else:
            pid_uri = namespace[term]

    if pid_uri.startswith(OSFIO):
        pid_uri = pid_uri.rstrip('/')

    # TODO: replace http with https (or vice versa, to match uri in LOCAL_CONTEXT)
    return pid_uri


def graph_equals(actual_rdf_graph, expected_triples):
    expected_rdf_graph = rdflib.Graph()
    for triple in expected_triples:
        expected_rdf_graph.add(triple)
    return rdflib.compare.isomorphic(
        actual_rdf_graph,
        expected_rdf_graph,
    )


class NormdToRdf:
    def __init__(self, normd):
        self._normd = normd
        self._rdfgraph = None
        self._blank_to_pid = None
        self._visited = None

    def build_rdf(self):
        self._reset()
        sharegraph = MutableGraph.from_jsonld(self._normd.data)
        focus_node = sharegraph.get_central_node(guess=True)
        self._sharegraphnode_to_rdf(focus_node)
        return self._rdfgraph, self._get_rdf_id(focus_node)

    def _reset(self):
        self._rdfgraph = contextualized_graph()
        self._blank_to_pid = {}
        self._visited = set()

    def _field_to_predicate_uri(self, type_name, field_name):
        # TODO: explicit map
        share_field = ShareV2Schema().get_field(type_name, field_name)
        if share_field and share_field.rdf_predicate:
            namespace, _, name = share_field.rdf_predicate.partition(':')
            return LOCAL_CONTEXT[namespace][name]
        return SHAREV2[field_name]

    def _type_to_uri(self, sharegraph_node):
        # TODO: explicit map
        return SHAREV2[sharegraph_node.type]

    def _sharegraphnode_to_rdf(self, sharegraph_node):
        if sharegraph_node.id in self._visited:
            return
        self._visited.add(sharegraph_node.id)

        node_id = self._get_rdf_id(sharegraph_node)
        self._rdfgraph.add((
            node_id,
            rdflib.RDF.type,
            self._type_to_uri(sharegraph_node),
        ))
        for attr_name, attr_value in sharegraph_node.attrs().items():
            self._rdfgraph.add((
                node_id,
                self._field_to_predicate_uri(sharegraph_node.type, attr_name),
                rdflib.Literal(attr_value),
            ))
        for relation_name, related in sharegraph_node.relations().items():
            if not isinstance(related, list):
                related = [related]
            for related_node in related:
                self._rdfgraph.add((
                    node_id,
                    self._field_to_predicate_uri(sharegraph_node.type, relation_name),
                    self._get_rdf_id(related_node)
                ))
                self._sharegraphnode_to_rdf(related_node)
