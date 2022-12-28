import rdflib

from share.util.graph import MutableGraph
from share.util import rdfutil


def sharev2_to_rdf(sharev2graph, focus_uri=None):
    if not isinstance(sharev2graph, MutableGraph):
        sharev2graph = MutableGraph.from_jsonld(sharev2graph)
    converter = Sharev2ToRdfConverter(sharev2graph, focus_uri)
    return (converter.focus_uri, converter.rdfgraph)


class Sharev2ToRdfConverter:
    def __init__(self, sharev2graph, focus_uri=None):
        self.sharev2graph = sharev2graph
        if focus_uri is None:
            self.focus_uri = None
        else:
            self.focus_uri = rdfutil.normalize_pid_uri(focus_uri)
        self._sharenodeid_to_rdfid = {}
        self._visited_sharenode_ids = set()
        self.rdfgraph = None
        self._fill_rdfgraph()

    def _fill_rdfgraph(self):
        assert self.rdfgraph is None
        self.rdfgraph = rdfutil.contextualized_graph()
        self._add_work(self._get_focus_worknode())

    def _get_focus_worknode(self):
        if self.focus_uri:
            for identifier_sharenode in self.sharev2graph.filter_type('workidentifier'):
                if rdfutil.pids_equal(self.focus_uri, identifier_sharenode['uri']):
                    return identifier_sharenode['creative_work']
        else:
            central_work = self.sharev2graph.get_central_node(guess=True)
            self.focus_uri = self._get_rdf_id(central_work)
            return central_work

    def _agentwork_relation_predicate(self, agent_relation):
        predicate_map = {
            'creator': rdfutil.DCT.creator,
            'publisher': rdfutil.DCT.publisher,
            'contributor': rdfutil.DCT.contributor,
            'principalinvestigator': rdfutil.DCT.contributor,
            'principalinvestigatorcontact': rdfutil.DCT.contributor,
        }
        predicate = predicate_map.get(agent_relation.type)
        return predicate or rdfutil.SHAREV2[agent_relation.type]

    def _agent_relation_predicate(self, agent_relation):
        predicate_map = {
            # TODO
        }
        predicate = predicate_map.get(agent_relation.type)
        return predicate or rdfutil.SHAREV2[agent_relation.type]

    def _work_relation_predicate(self, work_relation):
        predicate_map = {
            # TODO
        }
        predicate = predicate_map.get(work_relation.type)
        return predicate or rdfutil.SHAREV2[work_relation.type]

    def _add_agent(self, agent_sharenode):
        if agent_sharenode.id in self._visited_sharenode_ids:
            return  # avoid infinite loops
        self._visited_sharenode_ids.add(agent_sharenode.id)

        agent_id = self._get_rdf_id(agent_sharenode)

        self.rdfgraph.add((agent_id, rdflib.RDF.type, rdfutil.SHAREV2[agent_sharenode.type]))

        for attr_name, attr_value in agent_sharenode.attrs().items():
            if attr_value is None or attr_value == '' or attr_name == 'extra':
                continue
            self.rdfgraph.add((agent_id, rdfutil.SHAREV2[attr_name], rdflib.Literal(attr_value)))

        for relation_sharenode in agent_sharenode['outgoing_agent_relations']:
            related_agent = relation_sharenode['related']
            predicate_uri = self._agent_relation_predicate(relation_sharenode)
            self.rdfgraph.add((agent_id, predicate_uri, self._get_rdf_id(related_agent)))
            self._add_agent(related_agent)

    def _add_work(self, work_sharenode):
        if work_sharenode.id in self._visited_sharenode_ids:
            return  # avoid infinite loops
        self._visited_sharenode_ids.add(work_sharenode.id)

        work_id = self._get_rdf_id(work_sharenode)

        self.rdfgraph.add((work_id, rdflib.RDF.type, rdfutil.SHAREV2[work_sharenode.type]))
        self.rdfgraph.add((work_id, rdfutil.DCT.title, rdflib.Literal(work_sharenode['title'])))

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
            self.rdfgraph.add((work_id, rdfutil.DCT.subject, rdflib.Literal(subject_name)))

        description = work_sharenode['description']
        if description:
            self.rdfgraph.add((work_id, rdfutil.DCT.description, rdflib.Literal(description)))

        date = work_sharenode['date_published'] or work_sharenode['date_updated']
        if date:
            self.rdfgraph.add((work_id, rdfutil.DCT.date, rdflib.Literal(str(date))))

        identifier_uris = {
            identifier_node['uri']
            for identifier_node in work_sharenode['identifiers']
        }
        for identifier_uri in sorted(identifier_uris):
            self.rdfgraph.add((work_id, rdfutil.DCT.identifier, rdflib.Literal(identifier_uri)))

        language = work_sharenode['language']
        if language:
            self.rdfgraph.add((work_id, rdfutil.DCT.language, rdflib.Literal(language)))

        for relation_sharenode in work_sharenode['outgoing_creative_work_relations']:
            related_work = relation_sharenode['related']
            predicate_uri = self._work_relation_predicate(relation_sharenode)
            self.rdfgraph.add((work_id, predicate_uri, self._get_rdf_id(related_work)))
            self._add_work(related_work)

        if work_sharenode['rights']:
            self.rdfgraph.add((work_id, rdfutil.DCT.rights, rdflib.Literal(work_sharenode['rights'])))

        if work_sharenode['free_to_read_type']:
            self.rdfgraph.add((work_id, rdfutil.DCT.rights, rdflib.Literal(work_sharenode['free_to_read_type'])))

    def _get_related_uris(self, work_node):
        related_work_uris = set()
        for related_work_node in work_node['related_works']:
            related_work_uris.update(
                identifier['uri']
                for identifier in related_work_node['identifiers']
            )
        return sorted(related_work_uris)

    def _get_rdf_id(self, sharenode):
        cached_id = self._sharenodeid_to_rdfid.get(sharenode.id)
        if cached_id:
            return cached_id
        guessed_pid = self._guess_pid(sharenode)
        if guessed_pid:
            self._sharenodeid_to_rdfid[sharenode.id] = guessed_pid
            return guessed_pid
        blank_id = rdflib.term.BNode(sharenode.id)
        self._sharenodeid_to_rdfid[sharenode.id] = blank_id
        return blank_id

    def _guess_pid(self, sharenode):
        node_irls = sorted(filter(None, (
            identifier['uri']
            for identifier in (sharenode['identifiers'] or ())
        )))
        for uri in node_irls:
            if any(uri.startswith(ns) for ns in rdfutil.LOCAL_CONTEXT.values()):
                return rdfutil.normalize_pid_uri(uri)
        return None
