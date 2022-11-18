import re
from urllib.parse import urlsplit

import rdflib

from share.util.graph import MutableGraph
from share.util import rdfutil

from share.metadata_formats.base import MetadataFormatter


class RdfTurtleFormatter(MetadataFormatter):
    """builds an RDF graph and serializes it as turtle
    """

    def format(self, normalized_datum):
        rdf_graph, _ = self.build_rdf_graph(normalized_datum)
        return rdf_graph.serialize(format='turtle')

        # TODO
        # if (
        #     not central_work
        #     or central_work.concrete_type != 'abstractcreativework'
        #     or central_work['is_deleted']
        # ):
        #     return self.format_as_deleted(None)

    def build_rdf_graph(self, normalized_datum):
        self._reset()
        mgraph = MutableGraph.from_jsonld(normalized_datum.data)
        central_work = mgraph.get_central_node(guess=True)

        rdf_graph = rdfutil.contextualized_graph()
        self._add_work(rdf_graph, central_work)
        return rdf_graph, self._get_rdf_id(central_work)

    def _reset(self):
        self._blank_to_pid = {}

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
        }
        predicate = predicate_map.get(agent_relation.type)
        return predicate or rdfutil.SHAREV2[agent_relation.type]

    def _work_relation_predicate(self, work_relation):
        predicate_map = {
        }
        predicate = predicate_map.get(work_relation.type)
        return predicate or rdfutil.SHAREV2[work_relation.type]

    def _add_agent(self, rdf_graph, agent_sharenode):
        agent_id = self._get_rdf_id(agent_sharenode)

        rdf_graph.add((agent_id, rdflib.RDF.type, rdfutil.SHAREV2[agent_sharenode.type]))

        for attr_name, attr_value in agent_sharenode.attrs().items():
            if attr_value is None or attr_value == '' or attr_name == 'extra':
                continue
            rdf_graph.add((agent_id, rdfutil.SHAREV2[attr_name], rdflib.Literal(attr_value)))

        for relation_sharenode in agent_sharenode['outgoing_agent_relations']:
            related_agent = relation_sharenode['related']
            predicate_uri = self._agent_relation_predicate(relation_sharenode)
            rdf_graph.add((agent_id, predicate_uri, self._get_rdf_id(related_agent)))
            self._add_agent(rdf_graph, related_agent)

    def _add_work(self, rdf_graph, work_sharenode):
        work_id = self._get_rdf_id(work_sharenode)

        rdf_graph.add((work_id, rdflib.RDF.type, rdfutil.SHAREV2[work_sharenode.type]))
        rdf_graph.add((work_id, rdfutil.DCT.title, rdflib.Literal(work_sharenode['title'])))

        for relation_sharenode in work_sharenode['agent_relations']:
            related_agent = relation_sharenode['agent']
            predicate_uri = self._agentwork_relation_predicate(relation_sharenode)
            rdf_graph.add((work_id, predicate_uri, self._get_rdf_id(related_agent)))
            self._add_agent(rdf_graph, related_agent)

        subject_names = {
            subject_node['name']
            for subject_node in work_sharenode['subjects']
        }
        for subject_name in sorted(subject_names):
            # TODO: uri?
            rdf_graph.add((work_id, rdfutil.DCT.subject, rdflib.Literal(subject_name)))

        description = work_sharenode['description']
        if description:
            rdf_graph.add((work_id, rdfutil.DCT.description, rdflib.Literal(description)))

        date = work_sharenode['date_published'] or work_sharenode['date_updated']
        if date:
            rdf_graph.add((work_id, rdfutil.DCT.date, rdflib.Literal(str(date))))

        identifier_uris = {
            identifier_node['uri']
            for identifier_node in work_sharenode['identifiers']
        }
        for identifier_uri in sorted(identifier_uris):
            rdf_graph.add((work_id, rdfutil.DCT.identifier, rdflib.Literal(identifier_uri)))

        language = work_sharenode['language']
        if language:
            rdf_graph.add((work_id, rdfutil.DCT.language, rdflib.Literal(language)))

        for relation_sharenode in work_sharenode['outgoing_creative_work_relations']:
            related_work = relation_sharenode['related']
            predicate_uri = self._work_relation_predicate(relation_sharenode)
            rdf_graph.add((work_id, predicate_uri, self._get_rdf_id(related_work)))
            self._add_work(self, rdf_graph, related_work)

        if work_sharenode['rights']:
            rdf_graph.add((work_id, rdfutil.DCT.rights, rdflib.Literal(work_sharenode['rights'])))

        if work_sharenode['free_to_read_type']:
            rdf_graph.add((work_id, rdfutil.DCT.rights, rdflib.Literal(work_sharenode['free_to_read_type'])))

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
