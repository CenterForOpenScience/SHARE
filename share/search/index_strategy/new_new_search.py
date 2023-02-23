import json

from share.models.core import FormattedMetadataRecord
from share.search.index_strategy._base import IndexStrategy
from share.search.messages import MessageType


class NewNewIndexStrategy(IndexStrategy):
    @property
    def supported_message_types(self):
        return {MessageType.INDEX_SUID}

    @property
    def index_settings(self):
        return {
            'analysis': {
                'analyzer': {
                    'default': {
                        # same as 'standard' analyzer, plus html_strip
                        'type': 'custom',
                        'tokenizer': 'standard',
                        'filter': ['lowercase', 'stop'],
                        'char_filter': ['html_strip']
                    },
                },
            }
        }

    @property
    def index_mappings(self):
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
            'dynamic': 'strict',
            'properties': {
                'date_published': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                'date_updated': {'type': 'date', 'format': 'strict_date_optional_time', 'include_in_all': False},
                'description': {'type': 'text'},
                'id': {'type': 'keyword', 'include_in_all': False},
                'language': {'type': 'keyword', 'include_in_all': False},
                'source_name': {'type': 'keyword', 'include_in_all': False},
                'source_config': {'type': 'keyword', 'include_in_all': False},
                'source_unique_id': {'type': 'keyword'},
                'title': {'type': 'text', 'fields': exact_field},
            },
        }

    def build_action_generator(self, index_name, message_type):
        self.assert_message_type(message_type)

        action_template = {
            '_index': index_name,
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

