import json
import re

from django.conf import settings

from share.util.graph import MutableGraph
from share.util.names import get_related_agent_name
from share.util import IDObfuscator

from .base import MetadataFormatter


def format_type(type_name):
    # convert from PascalCase to lower case with spaces between words
    return re.sub(r'\B([A-Z])', r' \1', type_name).lower()


def format_node_type(node):
    return format_type(node.schema_type.name)


def format_node_type_lineage(node):
    return [format_type(t) for t in node.schema_type.type_lineage]


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

        suid = normalized_datum.raw.suid
        source_name = suid.source_config.source.long_title
        return json.dumps(strip_empty_values({
            'id': IDObfuscator.encode(suid),
            'sources': [source_name],
            'source_config': suid.source_config.label,
            'source_unique_id': suid.identifier,

            'type': format_node_type(central_work),
            'types': format_node_type_lineage(central_work),

            # attributes:
            'date_created': suid.get_date_first_seen().isoformat(),
            'date_modified': normalized_datum.created_at.isoformat(),
            'date_published': central_work['date_published'],
            'date_updated': central_work['date_updated'],
            'description': central_work['description'] or '',
            'justification': central_work['justification'],
            'language': central_work['language'],
            'registration_type': central_work['registration_type'],
            'retracted': bool(central_work['withdrawn']),
            'title': central_work['title'],
            'withdrawn': central_work['withdrawn'],

            'date': (
                central_work['date_published']
                or central_work['date_updated']
                or normalized_datum.created_at.isoformat()
            ),

            # agent relations:
            'affiliations': self._get_related_agent_names(central_work, ['agentworkrelation']),
            'contributors': self._get_related_agent_names(central_work, [
                'contributor',
                'creator',
                'principalinvestigator',
                'principalinvestigatorcontact',
            ]),
            'funders': self._get_related_agent_names(central_work, ['funder']),
            'publishers': self._get_related_agent_names(central_work, ['publisher']),
            'hosts': self._get_related_agent_names(central_work, ['host']),

            # other relations:
            'identifiers': [
                identifier_node['uri']
                for identifier_node in central_work['identifiers']
            ],
            'tags': [
                tag_node['name']
                for tag_node in central_work['tags']
            ],
            'subjects': self._get_subjects(central_work, source_name),
            'subject_synonyms': self._get_subject_synonyms(central_work),

            # osf-specific extra
            'osf_related_resource_types': (central_work['extra'] or {}).get('osf_related_resource_types'),

            # a bunch of nested data because reasons -- used mostly for rendering search results
            'lists': {
                'affiliations': self._build_related_agent_list(central_work, ['agentworkrelation']),
                'contributors': self._build_related_agent_list(central_work, [
                    'contributor',
                    'creator',
                    'principalinvestigator',
                    'principalinvestigatorcontact',
                ]),
                'funders': self._build_related_agent_list(central_work, ['funder']),
                'publishers': self._build_related_agent_list(central_work, ['publisher']),
                'hosts': self._build_related_agent_list(central_work, ['host']),
                'lineage': self._build_work_lineage(central_work),
            },
        }))

    def _get_related_agent_names(self, work_node, relation_types):
        return [
            get_related_agent_name(relation_node)
            for relation_node in work_node['agent_relations']
            if relation_node.type in relation_types
        ]

    def _get_subjects(self, work_node, source_name):
        return [
            self._serialize_subject(through_subject['subject'], source_name)
            for through_subject in work_node['subject_relations']
            if (
                not through_subject['is_deleted']
                and not through_subject['subject']['is_deleted']
            )
        ]

    def _get_subject_synonyms(self, work_node):
        return [
            self._serialize_subject(through_subject['subject']['central_synonym'])
            for through_subject in work_node['subject_relations']
            if (
                not through_subject['is_deleted']
                and not through_subject['subject']['is_deleted']
                and through_subject['subject']['central_synonym']
            )
        ]

    def _serialize_subject(self, subject_node, source_name=None):
        subject_lineage = [subject_node['name']]
        next_subject = subject_node['parent']
        while next_subject:
            subject_lineage.insert(0, next_subject['name'])
            next_subject = next_subject['parent']

        if source_name and subject_node['central_synonym']:
            taxonomy_name = source_name
        else:
            taxonomy_name = settings.SUBJECTS_CENTRAL_TAXONOMY

        subject_lineage.insert(0, taxonomy_name)
        return '|'.join(subject_lineage)

    def _build_list_agent(self, relation_node):
        agent_node = relation_node['agent']
        return {
            'type': format_node_type(agent_node),
            'types': format_node_type_lineage(agent_node),
            'name': agent_node['name'] or get_related_agent_name(relation_node),
            'given_name': agent_node['given_name'],
            'family_name': agent_node['family_name'],
            'additional_name': agent_node['additional_name'],
            'suffix': agent_node['suffix'],
            'identifiers': [
                identifier_node['uri']
                for identifier_node in agent_node['identifiers']
            ],
            'relation': format_node_type(relation_node),
            'order_cited': relation_node['order_cited'],
            'cited_as': relation_node['cited_as'],
        }

    def _build_related_agent_list(self, work_node, relation_types):
        return [
            self._build_list_agent(relation_node)
            for relation_node in work_node['agent_relations']
            if relation_node.type in relation_types
        ]

    def _build_work_lineage(self, work_node):
        try:
            parent_work = next(
                relation_node['related']
                for relation_node in work_node['outgoing_creative_work_relations']
                if relation_node.type == 'ispartof'
            )
        except StopIteration:
            return ()

        parent_lineage = self._build_work_lineage(parent_work)
        parent_data = {
            'type': format_node_type(parent_work),
            'types': format_node_type_lineage(parent_work),
            'title': parent_work['title'],
            'identifiers': [
                identifier_node['uri']
                for identifier_node in parent_work['identifiers']
            ],
        }
        return (
            *parent_lineage,
            parent_data,
        )
