import json

from share.models.core import FormattedMetadataRecord
from share.search.index_setup.base import IndexSetup
from share.search.messages import MessageType


class PostRendBackcompatIndexSetup(IndexSetup):
    SUBJECT_DELIMITER = '|'

    @property
    def supported_message_types(self):
        return {MessageType.INDEX_SUID}

    @property
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

    @property
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
                    'sources': {'type': 'keyword', 'include_in_all': False},
                    'subjects': {'type': 'text', 'include_in_all': False, 'analyzer': 'subject_analyzer', 'search_analyzer': 'subject_search_analyzer'},
                    'subject_synonyms': {'type': 'text', 'include_in_all': False, 'analyzer': 'subject_analyzer', 'search_analyzer': 'subject_search_analyzer', 'copy_to': 'subjects'},
                    'tags': {'type': 'text', 'fields': exact_field},
                    'title': {'type': 'text', 'fields': exact_field},
                    'type': {'type': 'keyword', 'include_in_all': False},
                    'types': {'type': 'keyword', 'include_in_all': False},
                    'withdrawn': {'type': 'boolean', 'include_in_all': False},
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

    def build_action_generator(self, index_name, message_type):
        self.assert_message_type(message_type)

        action_template = {
            '_index': index_name,
            '_type': 'creativeworks',
        }

        def action_generator(target_id_iter):
            record_qs = FormattedMetadataRecord.objects.filter(
                suid_id__in=target_id_iter,
                record_format='sharev2_elastic',  # TODO specify in config? or don't
            )
            for record in record_qs:
                source_doc = json.loads(record.formatted_metadata)
                if source_doc.pop('is_deleted', False):
                    action = {
                        **action_template,
                        '_id': source_doc['id'],
                        '_op_type': 'delete',
                    }
                else:
                    action = {
                        **action_template,
                        '_id': source_doc['id'],
                        '_op_type': 'index',
                        '_source': source_doc,
                    }
                yield (record.suid_id, action)
        return action_generator
