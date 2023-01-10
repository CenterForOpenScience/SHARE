import json
import re

import rdflib

from share.legacy_normalize.schema import ShareV2Schema
from share.util import IDObfuscator
from share.util import sharev2_to_rdf, rdfutil
from .base import MetadataFormatter


def format_sharev2_type(type_name):
    # convert from PascalCase to lower case with spaces between words
    return re.sub(r'\B([A-Z])', r' \1', type_name).lower()


def strip_namespace(uri, namespaces=None):
    if namespaces is None:
        namespaces = rdfutil.KNOWN_PID_NAMESPACES
    for namespace in namespaces:
        ns = str(namespace)
        if uri.startswith(ns):
            return uri[len(ns):]
    else:
        return None


def format_node_type(rdfgraph, node_id):
    type_id = rdfgraph.value(node_id, rdflib.RDF.type)
    return (
        format_sharev2_type(strip_namespace(type_id, [rdfutil.SHAREV2]))
        if type_id is not None
        else None
    )


def format_node_type_lineage(rdfgraph, node_id):
    type_id = rdfgraph.value(node_id, rdflib.RDF.type)
    if type_id:
        type_name = strip_namespace(type_id, [rdfutil.SHAREV2])
        if type_name:
            type_lineage = ShareV2Schema().get_type(type_name).type_lineage
            return [format_sharev2_type(t) for t in type_lineage]
    return None


def format_relation_type(predicate_id):
    return format_sharev2_type(strip_namespace(predicate_id))


def unwrapped_value(rdfgraph, focus_id, predicate_id, *, default=None):
    value = rdfgraph.value(focus_id, predicate_id)
    return (
        value.toPython()
        if value is not None
        else default
    )


# values that, for the purpose of indexing in elasticsearch, are equivalent to absence
EMPTY_VALUES = (None, '')


def strip_empty_values(thing):
    if isinstance(thing, dict):
        return {
            k: strip_empty_values(v)
            for k, v in thing.items()
            if v not in EMPTY_VALUES
        }
    if isinstance(thing, list):
        return [
            strip_empty_values(v)
            for v in thing
            if v not in EMPTY_VALUES
        ]
    if isinstance(thing, tuple):
        return tuple(
            strip_empty_values(v)
            for v in thing
            if v not in EMPTY_VALUES
        )
    return thing


class ShareV2ElasticFormatter(MetadataFormatter):
    def format(self, normalized_datum):
        rdfgraph = normalized_datum.get_rdfgraph()

        if not rdfgraph:
            return None
        print(rdfgraph.serialize(format='turtle'))

        suid = normalized_datum.raw.suid
        source_name = suid.source_config.source.long_title
        focus = rdfutil.normalize_pid_uri(suid.described_resource_pid)
        return json.dumps(strip_empty_values({
            # system properties (about the metadata record)
            'id': IDObfuscator.encode(suid),
            'sources': [source_name],
            'source_config': suid.source_config.label,
            'source_unique_id': suid.identifier,
            'date_created': suid.get_date_first_seen().isoformat(),
            'date_modified': normalized_datum.created_at.isoformat(),

            # metadata properties (about the described resource)
            'date': (
                rdfgraph.value(focus, rdfutil.DCT.available)
                or rdfgraph.value(focus, rdfutil.DCT.modified)
                or normalized_datum.created_at.isoformat()
            ),
            'date_published': rdfgraph.value(focus, rdfutil.DCT.available),
            'date_updated': rdfgraph.value(focus, rdfutil.DCT.modified),
            'description': rdfgraph.value(focus, rdfutil.DCT.description),
            'justification': rdfgraph.value(focus, rdfutil.SHAREV2.justification),
            'language': rdfgraph.value(focus, rdfutil.DCT.language),
            'registration_type': rdfgraph.value(focus, rdfutil.SHAREV2.registration_type),
            'retracted': bool(rdfgraph.value(focus, rdfutil.SHAREV2.withdrawn)),
            'title': rdfgraph.value(focus, rdfutil.DCT.title),
            'type': format_node_type(rdfgraph, focus),
            'types': format_node_type_lineage(rdfgraph, focus),
            'withdrawn': unwrapped_value(rdfgraph, focus, rdfutil.SHAREV2.withdrawn),

            # agent relations:
            'affiliations': self._get_related_agent_names(rdfgraph, focus, [rdfutil.SHAREV2.AgentWorkRelation]),
            'contributors': self._get_related_agent_names(rdfgraph, focus, [
                rdfutil.DCT.contributor,
                rdfutil.DCT.creator,
                rdfutil.SHAREV2.PrincipalInvestigator,
                rdfutil.SHAREV2.PrincipalInvestigatorContact,
            ]),
            'funders': self._get_related_agent_names(rdfgraph, focus, [rdfutil.SHAREV2.Funder]),
            'publishers': self._get_related_agent_names(rdfgraph, focus, [rdfutil.DCT.publisher]),
            'hosts': self._get_related_agent_names(rdfgraph, focus, [rdfutil.SHAREV2.Host]),

            # other relations:
            'identifiers': sorted(rdfgraph.objects(focus, rdfutil.DCT.identifier)),
            'tags': sorted(rdfgraph.objects(focus, rdfutil.SHAREV2.tag)),
            'subjects': sorted(rdfgraph.objects(focus, rdfutil.SHAREV2.subject)),
            'subject_synonyms': sorted(rdfgraph.objects(focus, rdfutil.SHAREV2.subject_synonym)),

            # osf-specific extra
            'osf_related_resource_types': self._get_osf_related_resource_types(rdfgraph, focus),

            # a bunch of nested data because reasons -- used mostly for rendering search results
            'lists': {
                'affiliations': self._build_related_agent_list(rdfgraph, focus, [rdfutil.SHAREV2.AgentWorkRelation]),
                'contributors': self._build_related_agent_list(rdfgraph, focus, [
                    rdfutil.DCT.contributor,
                    rdfutil.DCT.creator,
                    rdfutil.SHAREV2.PrincipalInvestigator,
                    rdfutil.SHAREV2.PrincipalInvestigatorContact,
                ]),
                'funders': self._build_related_agent_list(rdfgraph, focus, [rdfutil.SHAREV2.Funder]),
                'publishers': self._build_related_agent_list(rdfgraph, focus, [rdfutil.DCT.publisher]),
                'hosts': self._build_related_agent_list(rdfgraph, focus, [rdfutil.SHAREV2.Host]),
                'lineage': self._build_work_lineage(rdfgraph, focus),
            },
        }))

    def _get_related_agents(self, rdfgraph, focus, predicate_ids):
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
                rdfutil.SHAREV2.order_cited,
                default=99999,
            )
        return sorted(related_list, key=sort_key)

    def _get_related_agent_names(self, rdfgraph, focus, predicate_ids):
        return [
            sharev2_to_rdf.get_related_agent_name(rdfgraph, related_id)
            for _, related_id in self._get_related_agents(rdfgraph, focus, predicate_ids)
        ]

    def _get_osf_related_resource_types(self, rdfgraph, focus):
        related_resource_types = {}
        for resource_type in rdfgraph.objects(focus, rdfutil.OSF.has_related_resource_type):
            related_resource_types[resource_type] = True
        for resource_type in rdfgraph.objects(focus, rdfutil.OSF.lacks_related_resource_type):
            related_resource_types[resource_type] = False
        return related_resource_types or None

    def _build_list_agent(self, rdfgraph, predicate_id, related_id):
        return {
            'type': format_node_type(rdfgraph, related_id),
            'types': format_node_type_lineage(rdfgraph, related_id),
            'name': sharev2_to_rdf.get_related_agent_name(rdfgraph, related_id),
            'given_name': rdfgraph.value(related_id, rdfutil.SHAREV2.given_name),
            'family_name': rdfgraph.value(related_id, rdfutil.SHAREV2.family_name),
            'additional_name': rdfgraph.value(related_id, rdfutil.SHAREV2.additional_name),
            'suffix': rdfgraph.value(related_id, rdfutil.SHAREV2.suffix),
            'identifiers': list(rdfgraph.objects(related_id, rdfutil.DCT.identifier)),
            'relation': format_relation_type(predicate_id),
            'order_cited': unwrapped_value(rdfgraph, related_id, rdfutil.SHAREV2.order_cited),
            'cited_as': rdfgraph.value(related_id, rdfutil.SHAREV2.cited_as),
        }

    def _build_related_agent_list(self, rdfgraph, focus, predicate_ids):
        return [
            self._build_list_agent(rdfgraph, predicate_id, related_id)
            for predicate_id, related_id in self._get_related_agents(rdfgraph, focus, predicate_ids)
        ]

    def _build_work_lineage(self, rdfgraph, focus):
        parent_work_id = rdfgraph.value(focus, rdfutil.SHAREV2.IsPartOf)
        if not parent_work_id:
            return ()
        parent_lineage = self._build_work_lineage(rdfgraph, parent_work_id)
        parent_data = {
            'type': format_node_type(rdfgraph, parent_work_id),
            'types': format_node_type_lineage(rdfgraph, parent_work_id),
            'title': rdfgraph.value(parent_work_id, rdfutil.DCT.title),
            'identifiers': list(rdfgraph.objects(parent_work_id, rdfutil.DCT.identifier)),
        }
        return (
            *parent_lineage,
            parent_data,
        )
