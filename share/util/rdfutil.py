import re
from urllib.parse import urlsplit

import rdflib
import rdflib.compare

from share import exceptions


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
        raise exceptions.BadPid(f'does not look like a URI: {pid_uri}')
    pid_uri = pid_uri.strip()
    if '://' not in pid_uri:
        # is shortened form, 'prefix:term'
        (namespace_prefix, _, term) = pid_uri.partition(':')
        try:
            namespace = LOCAL_CONTEXT[namespace_prefix]
        except KeyError:
            raise exceptions.BadPid(f'unknown uri prefix "{namespace_prefix}" from uri "{pid_uri}"')
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


class Sharev2ToRdf:
    def __init__(self, mgraph):
        self.mgraph = mgraph
        self.rdfgraph = None
        self.focus_uri = None
        self._blank_to_pid = {}
        self._fill_rdfgraph()

    def _fill_rdfgraph(self):
        assert self.rdfgraph is None
        self.rdfgraph = contextualized_graph()
        central_work = self.mgraph.get_central_node(guess=True)
        self._add_work(central_work)
        self.focus_uri = self._get_rdf_id(central_work)

    def _agentwork_relation_predicate(self, agent_relation):
        predicate_map = {
            'creator': DCT.creator,
            'publisher': DCT.publisher,
            'contributor': DCT.contributor,
            'principalinvestigator': DCT.contributor,
            'principalinvestigatorcontact': DCT.contributor,
        }
        predicate = predicate_map.get(agent_relation.type)
        return predicate or SHAREV2[agent_relation.type]

    def _agent_relation_predicate(self, agent_relation):
        predicate_map = {
        }
        predicate = predicate_map.get(agent_relation.type)
        return predicate or SHAREV2[agent_relation.type]

    def _work_relation_predicate(self, work_relation):
        predicate_map = {
        }
        predicate = predicate_map.get(work_relation.type)
        return predicate or SHAREV2[work_relation.type]

    def _add_agent(self, agent_sharenode):
        agent_id = self._get_rdf_id(agent_sharenode)

        self.rdfgraph.add((agent_id, rdflib.RDF.type, SHAREV2[agent_sharenode.type]))

        for attr_name, attr_value in agent_sharenode.attrs().items():
            if attr_value is None or attr_value == '' or attr_name == 'extra':
                continue
            self.rdfgraph.add((agent_id, SHAREV2[attr_name], rdflib.Literal(attr_value)))

        for relation_sharenode in agent_sharenode['outgoing_agent_relations']:
            related_agent = relation_sharenode['related']
            predicate_uri = self._agent_relation_predicate(relation_sharenode)
            self.rdfgraph.add((agent_id, predicate_uri, self._get_rdf_id(related_agent)))
            self._add_agent(related_agent)

    def _add_work(self, work_sharenode):
        work_id = self._get_rdf_id(work_sharenode)

        self.rdfgraph.add((work_id, rdflib.RDF.type, SHAREV2[work_sharenode.type]))
        self.rdfgraph.add((work_id, DCT.title, rdflib.Literal(work_sharenode['title'])))

        for relation_sharenode in work_sharenode['agent_relations']:
            related_agent = relation_sharenode['agent']
            predicate_uri = self._agentwork_relation_predicate(relation_sharenode)
            self.rdfgraph.add((work_id, predicate_uri, self._get_rdf_id(related_agent)))
            self._add_agent(related_agent)

        subject_names = {
            subject_node['name']
            for subject_node in work_sharenode['subjects']
        }
        for subject_name in sorted(subject_names):
            # TODO: uri?
            self.rdfgraph.add((work_id, DCT.subject, rdflib.Literal(subject_name)))

        description = work_sharenode['description']
        if description:
            self.rdfgraph.add((work_id, DCT.description, rdflib.Literal(description)))

        date = work_sharenode['date_published'] or work_sharenode['date_updated']
        if date:
            self.rdfgraph.add((work_id, DCT.date, rdflib.Literal(str(date))))

        identifier_uris = {
            identifier_node['uri']
            for identifier_node in work_sharenode['identifiers']
        }
        for identifier_uri in sorted(identifier_uris):
            self.rdfgraph.add((work_id, DCT.identifier, rdflib.Literal(identifier_uri)))

        language = work_sharenode['language']
        if language:
            self.rdfgraph.add((work_id, DCT.language, rdflib.Literal(language)))

        for relation_sharenode in work_sharenode['outgoing_creative_work_relations']:
            related_work = relation_sharenode['related']
            predicate_uri = self._work_relation_predicate(relation_sharenode)
            self.rdfgraph.add((work_id, predicate_uri, self._get_rdf_id(related_work)))
            self._add_work(related_work)

        if work_sharenode['rights']:
            self.rdfgraph.add((work_id, DCT.rights, rdflib.Literal(work_sharenode['rights'])))

        if work_sharenode['free_to_read_type']:
            self.rdfgraph.add((work_id, DCT.rights, rdflib.Literal(work_sharenode['free_to_read_type'])))

    def _get_related_uris(self, work_node):
        related_work_uris = set()
        for related_work_node in work_node['related_works']:
            related_work_uris.update(
                identifier['uri']
                for identifier in related_work_node['identifiers']
            )
        return sorted(related_work_uris)

    def _get_rdf_id(self, sharenode):
        cached_id = self._blank_to_pid.get(sharenode.id)
        if cached_id:
            return cached_id
        guessed_pid = self._guess_pid(sharenode)
        if guessed_pid:
            pid = rdflib.URIRef(guessed_pid)
            self._blank_to_pid[sharenode.id] = pid
            return pid
        blank_id = rdflib.term.BNode(sharenode.id)
        self._blank_to_pid[sharenode.id] = blank_id
        return blank_id

    def _guess_pid(self, sharenode):
        pid_domain_regexes = [
            re.compile(r'osf\.io'),
            re.compile(r'([^./]+\.)?doi\.org'),
            re.compile(r'orcid\.org'),
            # TODO: more (or a different approach)
        ]
        node_irls = sorted(
            identifier['uri']
            for identifier in (sharenode['identifiers'] or ())
        )
        irl_domains = {
            node_irl: urlsplit(node_irl).hostname
            for node_irl in node_irls
        }
        for domain_regex in pid_domain_regexes:
            for node_irl, domain in irl_domains.items():
                if domain_regex.fullmatch(domain):
                    return node_irl.replace('http:', 'https:').rstrip('/')
        return None
