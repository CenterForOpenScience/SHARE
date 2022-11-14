from rdflib import DCTERMS

from share.util.graph import MutableGraph
from share.util import rdfutil

from share.metadata_formats.base import MetadataFormatter


class RdfTurtleFormatter(MetadataFormatter):
    """builds an RDF graph and serializes it as turtle
    """

    def format(self, normalized_datum):
        mgraph = MutableGraph.from_jsonld(normalized_datum.data)
        central_work = mgraph.get_central_node(guess=True)

        if (
            not central_work
            or central_work.concrete_type != 'abstractcreativework'
            or central_work['is_deleted']
        ):
            return self.format_as_deleted(None)

        rdf_graph = self.build_rdf_graph(central_work)
        return rdf_graph.serialize(format='turtle')

    def rdf_triples(self, work_node):
        rdf_graph = rdfutil.contextualized_graph()
        SubEl(dc_element, ns('dc', 'title'), work_node['title'])

        for creator_name in self._get_related_agent_names(work_node, {'creator'}):
            SubEl(dc_element, ns('dc', 'creator'), creator_name)

        subject_names = {
            subject_node['name']
            for subject_node in work_node['subjects']
        }
        for subject_name in sorted(subject_names):
            SubEl(dc_element, ns('dc', 'subject'), subject_name)

        description = work_node['description']
        if description:
            SubEl(dc_element, ns('dc', 'description'), description)

        for publisher_name in sorted(self._get_related_agent_names(work_node, {'publisher'})):
            SubEl(dc_element, ns('dc', 'publisher'), publisher_name)

        for contributor_name in sorted(self._get_related_agent_names(work_node, {'contributor', 'principalinvestigator', 'principalinvestigatorcontact'})):
            SubEl(dc_element, ns('dc', 'contributor'), contributor_name)

        date = work_node['date_published'] or work_node['date_updated']
        if date:
            SubEl(dc_element, ns('dc', 'date'), format_datetime(date))

        SubEl(dc_element, ns('dc', 'type'), work_node.type)

        identifier_uris = {
            identifier_node['uri']
            for identifier_node in work_node['identifiers']
        }
        for identifier_uri in sorted(identifier_uris):
            SubEl(dc_element, ns('dc', 'identifier'), identifier_uri)

        language = work_node['language']
        if language:
            SubEl(dc_element, ns('dc', 'language'), language)

        for related_uri in self._get_related_uris(work_node):
            SubEl(dc_element, ns('dc', 'relation'), related_uri)

        if work_node['rights']:
            SubEl(dc_element, ns('dc', 'rights'), work_node['rights'])

        if work_node['free_to_read_type']:
            SubEl(dc_element, ns('dc', 'rights'), work_node['free_to_read_type'])

        return dc_element

    def _get_related_agent_names(self, work_node, relation_types):
        def sort_key(relation_node):
            order_cited = relation_node['order_cited']
            if order_cited is None:
                return 9999999  # those without order_cited go last
            return int(order_cited)

        relation_nodes = sorted(
            [
                relation_node
                for relation_node in work_node['agent_relations']
                if relation_node.type in relation_types
            ],
            key=sort_key,
        )

        # remove falsy values
        return filter(None, [
            get_related_agent_name(relation)
            for relation in relation_nodes
        ])

    def _get_related_uris(self, work_node):
        related_work_uris = set()
        for related_work_node in work_node['related_works']:
            related_work_uris.update(
                identifier['uri']
                for identifier in related_work_node['identifiers']
            )
        return sorted(related_work_uris)
