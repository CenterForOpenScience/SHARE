import json

from share.models import FormattedMetadataRecord, SourceUniqueIdentifier
from share.search.messages import MessageType
from share.search.index_strategy.elastic5 import Elastic5IndexStrategy
from share.util import IDObfuscator


class Sharev2Elastic5IndexStrategy(Elastic5IndexStrategy):
    SUBJECT_DELIMITER = '|'

    @property
    def supported_message_types(self):
        return {MessageType.INDEX_SUID}

    def index_settings(self):
        return {
            'analysis': {
                'filter': {
                    'autocomplete_filter': {
                        'type': 'edge_ngram',
                        'min_gram': 1,
                        'max_gram': 20
                    }
                },
                'analyzer': {
                    'default': {
                        # same as 'standard' analyzer, plus html_strip
                        'type': 'custom',
                        'tokenizer': 'standard',
                        'filter': ['lowercase', 'stop'],
                        'char_filter': ['html_strip']
                    },
                    'autocomplete': {
                        'type': 'custom',
                        'tokenizer': 'standard',
                        'filter': [
                            'lowercase',
                            'autocomplete_filter'
                        ]
                    },
                    'subject_analyzer': {
                        'type': 'custom',
                        'tokenizer': 'subject_tokenizer',
                        'filter': [
                            'lowercase',
                        ]
                    },
                    'subject_search_analyzer': {
                        'type': 'custom',
                        'tokenizer': 'keyword',
                        'filter': [
                            'lowercase',
                        ]
                    },
                },
                'tokenizer': {
                    'subject_tokenizer': {
                        'type': 'path_hierarchy',
                        'delimiter': self.SUBJECT_DELIMITER,
                    }
                }
            }
        }

    def index_mappings(self):
        autocomplete_field = {
            'autocomplete': {
                'type': 'string',
                'analyzer': 'autocomplete',
                'search_analyzer': 'standard',
                'include_in_all': False
            }
        }

        exact_field = {
            'exact': {
                'type': 'keyword',
                # From Elasticsearch documentation:
                # The value for ignore_above is the character count, but Lucene counts bytes.
                # If you use UTF-8 text with many non-ASCII characters, you may want to set the limit to 32766 / 3 = 10922 since UTF-8 characters may occupy at most 3 bytes
                'ignore_above': 10922
            }
        }

        return {
            'creativeworks': {
                'dynamic': 'strict',
                'properties': {
                    'affiliations': {'type': 'text', 'fields': exact_field},
                    'contributors': {'type': 'text', 'fields': exact_field},
                    'date': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                    'date_created': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                    'date_modified': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                    'date_published': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                    'date_updated': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                    'description': {'type': 'text'},
                    'funders': {'type': 'text', 'fields': exact_field},
                    'hosts': {'type': 'text', 'fields': exact_field},
                    'id': {'type': 'keyword', 'include_in_all': False},
                    'identifiers': {'type': 'text', 'fields': exact_field},
                    'justification': {'type': 'text', 'include_in_all': False},
                    'language': {'type': 'keyword', 'include_in_all': False},
                    'publishers': {'type': 'text', 'fields': exact_field},
                    'registration_type': {'type': 'keyword', 'include_in_all': False},
                    'retracted': {'type': 'boolean', 'include_in_all': False},
                    'source_config': {'type': 'keyword', 'include_in_all': False},
                    'source_unique_id': {'type': 'keyword'},
                    'sources': {'type': 'keyword', 'include_in_all': False},
                    'subjects': {'type': 'text', 'include_in_all': False, 'analyzer': 'subject_analyzer', 'search_analyzer': 'subject_search_analyzer'},
                    'subject_synonyms': {'type': 'text', 'include_in_all': False, 'analyzer': 'subject_analyzer', 'search_analyzer': 'subject_search_analyzer', 'copy_to': 'subjects'},
                    'tags': {'type': 'text', 'fields': exact_field},
                    'title': {'type': 'text', 'fields': exact_field},
                    'type': {'type': 'keyword', 'include_in_all': False},
                    'types': {'type': 'keyword', 'include_in_all': False},
                    'withdrawn': {'type': 'boolean', 'include_in_all': False},
                    'osf_related_resource_types': {'type': 'object', 'dynamic': True, 'include_in_all': False},
                    'lists': {'type': 'object', 'dynamic': True, 'include_in_all': False},
                },
                'dynamic_templates': [
                    {'exact_field_on_lists_strings': {'path_match': 'lists.*', 'match_mapping_type': 'string', 'mapping': {'type': 'text', 'fields': exact_field}}},
                ]
            },
            'agents': {
                'dynamic': False,
                'properties': {
                    'id': {'type': 'keyword', 'include_in_all': False},
                    'identifiers': {'type': 'text', 'fields': exact_field},
                    'name': {'type': 'text', 'fields': {**autocomplete_field, **exact_field}},
                    'family_name': {'type': 'text', 'include_in_all': False},
                    'given_name': {'type': 'text', 'include_in_all': False},
                    'additional_name': {'type': 'text', 'include_in_all': False},
                    'suffix': {'type': 'text', 'include_in_all': False},
                    'location': {'type': 'text', 'include_in_all': False},
                    'sources': {'type': 'keyword', 'include_in_all': False},
                    'type': {'type': 'keyword', 'include_in_all': False},
                    'types': {'type': 'keyword', 'include_in_all': False},
                }
            },
            'sources': {
                'dynamic': False,
                'properties': {
                    'id': {'type': 'keyword', 'include_in_all': False},
                    'name': {'type': 'text', 'fields': {**autocomplete_field, **exact_field}},
                    'short_name': {'type': 'keyword', 'include_in_all': False},
                    'type': {'type': 'keyword', 'include_in_all': False},
                }
            },
            'tags': {
                'dynamic': False,
                'properties': {
                    'id': {'type': 'keyword', 'include_in_all': False},
                    'name': {'type': 'text', 'fields': {**autocomplete_field, **exact_field}},
                    'type': {'type': 'keyword', 'include_in_all': False},
                }
            },
        }

    def build_elastic_actions(self, message_type, messages_chunk):
        self.assert_message_type(message_type)
        action_template = {
            '_index': self.current_index_name,
        }
        suid_ids = set(message.target_id for message in messages_chunk)
        record_qs = FormattedMetadataRecord.objects.filter(
            suid_id__in=suid_ids,
            record_format='sharev2_elastic',  # TODO specify in config? or don't
        )
        for record in record_qs:
            doc_id = IDObfuscator.encode_id(record.suid_id, SourceUniqueIdentifier)
            suid_ids.pop(record.suid_id)
            source_doc = json.loads(record.formatted_metadata)
            assert source_doc['id'] == doc_id
            if source_doc.pop('is_deleted', False):
                action = {
                    **action_template,
                    '_id': doc_id,
                    '_op_type': 'delete',
                }
            else:
                action = {
                    **action_template,
                    '_id': doc_id,
                    '_op_type': 'index',
                    '_source': source_doc,
                }
            yield action
        # delete any that don't have the expected FormattedMetadataRecord
        for leftover_suid_id in suid_ids:
            yield {
                **action_template,
                '_id': IDObfuscator.encode_id(leftover_suid_id, SourceUniqueIdentifier),
                '_op_type': 'delete',
            }
