import rdflib

from django.conf import settings

from share import exceptions
from share.util.graph import MutableGraph
from share.util import rdfutil


def convert(sharev2graph, focus_uri, *, custom_subject_taxonomy_name):
    if not isinstance(sharev2graph, MutableGraph):
        sharev2graph = MutableGraph.from_jsonld(sharev2graph)
    converter = Sharev2ToRdfConverter(
        sharev2graph,
        rdfutil.normalize_pid_uri(focus_uri),
        custom_subject_taxonomy_name=custom_subject_taxonomy_name,
    )
    return converter.rdfgraph


def guess_pid(sharev2node):
    node_uris = sorted(filter(None, (
        identifier['uri']
        for identifier in (sharev2node['identifiers'] or ())
    )))
    for uri in node_uris:
        try:
            return rdfutil.normalize_pid_uri(uri, require_known_namespace=True)
        except exceptions.BadPid:
            pass
    return None


def get_related_agent_name(rdfgraph, related_id):
    """get the name to refer to a related agent

    @param rdfgraph: rdflib.Graph instance
    @param related_id: related agent node in the graph (could be bnode, uriref, or literal)
    @returns string (possibly empty)
    """
    if isinstance(related_id, rdflib.Literal):
        agent_name = str(related_id)
    else:
        agent_name = rdfgraph.value(related_id, rdfutil.SHAREV2.cited_as)
        if not agent_name:
            agent_name = rdfgraph.value(related_id, rdfutil.SHAREV2.name)
            if not agent_name:
                name_parts = filter(None, [
                    rdfgraph.value(related_id, rdfutil.SHAREV2.given_name),
                    rdfgraph.value(related_id, rdfutil.SHAREV2.additional_name),
                    rdfgraph.value(related_id, rdfutil.SHAREV2.family_name),
                    rdfgraph.value(related_id, rdfutil.SHAREV2.suffix),
                ])
                agent_name = ' '.join(name_parts).strip()
    return agent_name


class Sharev2ToRdfConverter:
    def __init__(self, sharev2graph, focus_uri, *, custom_subject_taxonomy_name):
        self.sharev2graph = sharev2graph
        assert isinstance(focus_uri, rdflib.URIRef)
        self.focus_uri = focus_uri
        self._custom_subject_taxonomy_name = (
            custom_subject_taxonomy_name
            or settings.SUBJECTS_CENTRAL_TAXONOMY
        )
        self._builder = None
        self._sharenodeid_to_rdfid = {}
        self._visited_sharenode_ids = set()
        self._fill_rdfgraph()

    @property
    def rdfgraph(self):
        assert self._builder is not None
        return self._builder.rdfgraph

    def _fill_rdfgraph(self):
        assert self._builder is None
        self._builder = rdfutil.RdfBuilder()
        self._add_work(self._get_focus_worknode())

    def _get_focus_worknode(self):
        for identifier_sharenode in self.sharev2graph.filter_type('workidentifier'):
            if rdfutil.pids_equal(self.focus_uri, identifier_sharenode['uri']):
                return identifier_sharenode['creative_work']

    def _agentwork_relation_predicate(self, agentwork_relation):
        predicate_map = {
            'Creator': rdfutil.DCT.creator,
            'Contributor': rdfutil.DCT.contributor,
            'Publisher': rdfutil.DCT.publisher,
            # 'principalinvestigator': rdfutil.DCT.contributor,
            # 'principalinvestigatorcontact': rdfutil.DCT.contributor,
        }
        type_name = agentwork_relation.schema_type.name
        predicate = predicate_map.get(type_name)
        return predicate or rdfutil.SHAREV2[type_name]

    def _agent_relation_predicate(self, agent_relation):
        predicate_map = {
            # TODO
        }
        type_name = agent_relation.schema_type.name
        predicate = predicate_map.get(type_name)
        return predicate or rdfutil.SHAREV2[type_name]

    def _work_relation_predicate(self, work_relation):
        predicate_map = {
            # TODO
        }
        type_name = work_relation.schema_type.name
        predicate = predicate_map.get(type_name)
        return predicate or rdfutil.SHAREV2[type_name]

    def _add_agent(self, agent_sharenode):
        if agent_sharenode.id in self._visited_sharenode_ids:
            return  # avoid infinite loops
        self._visited_sharenode_ids.add(agent_sharenode.id)

        agent_id = self._get_rdf_id(agent_sharenode)

        self._builder.add(agent_id, rdflib.RDF.type, rdfutil.SHAREV2[agent_sharenode.schema_type.name])
        self._add_identifiers(agent_sharenode)

        for attr_name, attr_value in agent_sharenode.attrs().items():
            skip_attr = (
                attr_value is None
                or attr_value == ''
                or attr_name == 'extra'
            )
            if skip_attr:
                continue
            # TODO: explicit attr_name-to-pid map
            self._builder.add(agent_id, rdfutil.SHAREV2[attr_name], attr_value)

        for relation_sharenode in agent_sharenode['outgoing_agent_relations']:
            related_agent = relation_sharenode['related']
            predicate_uri = self._agent_relation_predicate(relation_sharenode)
            self._builder.add(agent_id, predicate_uri, self._get_rdf_id(related_agent))
            self._add_agent(related_agent)

    def _add_work(self, work_sharenode):
        if work_sharenode.id in self._visited_sharenode_ids:
            return  # avoid infinite loops
        self._visited_sharenode_ids.add(work_sharenode.id)

        if work_sharenode['is_deleted']:
            return

        work_id = self._get_rdf_id(work_sharenode)
        self._builder.add(work_id, rdflib.RDF.type, rdfutil.SHAREV2[work_sharenode.schema_type.name])
        self._add_identifiers(work_sharenode)

        simply_mapped = {
            'title': rdfutil.DCT.title,
            'description': rdfutil.DCT.description,
            'date_published': rdfutil.DCT.available,
            'date_updated': rdfutil.DCT.modified,
            'language': rdfutil.DCT.language,
            'rights': rdfutil.DCT.rights,
        }
        for shareattr, predicate_uri in simply_mapped.items():
            self._builder.add(work_id, predicate_uri, work_sharenode[shareattr])

        unmapped = {
            'free_to_read_type',
            'free_to_read_date',
            'registration_type',
            'withdrawn',
            'justification',
        }
        for shareattr in unmapped:
            self._builder.add(work_id, rdfutil.SHAREV2[shareattr], work_sharenode[shareattr])

        for relation_sharenode in work_sharenode['agent_relations']:
            related_agent = relation_sharenode['agent']
            predicate_uri = self._agentwork_relation_predicate(relation_sharenode)
            agent_id = self._get_rdf_id(related_agent)
            self._builder.add(work_id, predicate_uri, agent_id)
            self._builder.add(agent_id, rdfutil.SHAREV2.cited_as, relation_sharenode['cited_as'])
            self._builder.add(agent_id, rdfutil.SHAREV2.order_cited, relation_sharenode['order_cited'])
            self._add_agent(related_agent)

        for subject_relation_sharenode in work_sharenode['subject_relations']:
            if not subject_relation_sharenode['is_deleted']:
                self._add_subject(work_id, subject_relation_sharenode['subject'])

        tag_names = {
            tag_node['name']
            for tag_node in work_sharenode['tags']
        }
        for tag_name in sorted(tag_names):
            self._builder.add(work_id, rdfutil.SHAREV2.tag, tag_name)

        try:
            osf_related_resource_types = work_sharenode['extra']['osf_related_resource_types']
        except (TypeError, KeyError):
            pass
        else:
            for related_resource_type, has_resource_of_type in osf_related_resource_types.items():
                pred = (
                    rdfutil.OSF.has_related_resource_type
                    if has_resource_of_type
                    else rdfutil.OSF.lacks_related_resource_type
                )
                self._builder.add(work_id, pred, related_resource_type)

        for relation_sharenode in work_sharenode['outgoing_creative_work_relations']:
            related_work = relation_sharenode['related']
            predicate_uri = self._work_relation_predicate(relation_sharenode)
            self._builder.add(work_id, predicate_uri, self._get_rdf_id(related_work))
            self._add_work(related_work)

    def _add_subject(self, work_id, subject_sharenode):
        should_skip = (
            (not subject_sharenode)
            or subject_sharenode['is_deleted']
        )
        if should_skip:
            return None
        lineage = self._get_subject_lineage(subject_sharenode)
        for subject_name in lineage:
            self._builder.add(work_id, rdfutil.DCT.subject, subject_name)
        central_synonym_sharenode = subject_sharenode['central_synonym']
        taxonomy_name = (
            self._custom_subject_taxonomy_name
            if central_synonym_sharenode
            else settings.SUBJECTS_CENTRAL_TAXONOMY
        )
        self._builder.add(
            work_id,
            rdfutil.SHAREV2.subject,
            '|'.join([taxonomy_name, *lineage])
        )
        if central_synonym_sharenode:
            synonym_lineage = self._get_subject_lineage(central_synonym_sharenode)
            self._builder.add(
                work_id,
                rdfutil.SHAREV2.subject_synonym,
                '|'.join([settings.SUBJECTS_CENTRAL_TAXONOMY, *synonym_lineage])
            )

    def _get_subject_lineage(self, subject_sharenode):
        if subject_sharenode is None:
            return []
        parent_lineage = self._get_subject_lineage(subject_sharenode['parent'])
        return [*parent_lineage, subject_sharenode['name']]

    def _add_identifiers(self, sharenode):
        node_id = self._get_rdf_id(sharenode)
        identifier_uris = {
            identifier_node['uri']
            for identifier_node in sharenode['identifiers']
        }
        for identifier_uri in sorted(identifier_uris):
            try:
                pid = rdfutil.normalize_pid_uri(identifier_uri)
            except exceptions.BadPid:
                self._builder.add(node_id, rdfutil.DCT.identifier, str(identifier_uri))
            else:
                self._builder.add(node_id, rdfutil.DCT.identifier, str(pid))
                if pid != node_id:
                    self._builder.add(node_id, rdflib.OWL.sameAs, pid)

    def _get_rdf_id(self, sharenode):
        cached_id = self._sharenodeid_to_rdfid.get(sharenode.id)
        if cached_id:
            return cached_id
        guessed_pid = guess_pid(sharenode)
        if guessed_pid:
            self._sharenodeid_to_rdfid[sharenode.id] = guessed_pid
            return guessed_pid
        blank_id = rdflib.term.BNode()
        self._sharenodeid_to_rdfid[sharenode.id] = blank_id
        return blank_id
