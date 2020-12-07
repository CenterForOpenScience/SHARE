import json

from django.conf import settings

from share.util.graph import MutableGraph

from .base import MetadataFormatter


class ShareV2ElasticFormatter(MetadataFormatter):
    def format(self, normalized_datum):
        mgraph = MutableGraph.from_jsonld(normalized_datum.data)
        central_work = mgraph.get_central_node(guess=True)

        if not central_work or central_work.concrete_type != 'abstractcreativework':
            return None

        suid = normalized_datum.raw.suid
        source_name = suid.source_config.source.long_title

        return json.dumps({
            'id': suid.id,
            'sources': [source_name],

            # attributes:
            'date_created': normalized_datum.created_at.isoformat(),  # TODO do another query to get the first normd under the same suid -- unsure how important
            'date_modified': normalized_datum.created_at.isoformat(),
            'date_published': central_work['date_published'],
            'date_updated': central_work['date_updated'],
            'description': central_work['description'],
            'justification': central_work['justification'],
            'language': central_work['language'],
            'registration_type': central_work['registration_type'],
            'retracted': central_work['withdrawn'],
            'title': central_work['title'],
            'type': central_work.type,
            'withdrawn': central_work['withdrawn'],

            'date': (
                central_work['date_published']
                or central_work['date_updated']
                or normalized_datum.created_at.isoformat()
            ),
            'types': central_work.schema_type.type_lineage,

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
        })

    def _get_related_agent_names(self, work_node, relation_types):
        return [
            relation_node['cited_as'] or relation_node['agent']['name']
            for relation_node in work_node['agent_relations']
            if relation_node.type in relation_types
        ]

    def _get_subjects(self, work_node, source_name):
        return [
            self._serialize_subject(subject_node, source_name)
            for subject_node in work_node['subjects']
        ]

    def _get_subject_synonyms(self, work_node):
        return [
            self._serialize_subject(subject_node['central_synonym'])
            for subject_node in work_node['subjects']
            if subject_node['central_synonym']
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
            'type': agent_node.type,
            'name': agent_node['name'],
            'given_name': agent_node['given_name'],
            'family_name': agent_node['family_name'],
            'additional_name': agent_node['additional_name'],
            'suffix': agent_node['suffix'],
            'identifiers': [
                identifier_node['uri']
                for identifier_node in agent_node['identifiers']
            ],
            'relation_type': relation_node.type,
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
            'type': parent_work.type,
            'types': parent_work.schema_type.type_lineage,
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
