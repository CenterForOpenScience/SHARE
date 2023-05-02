import json

import elasticsearch8

from share import models as db
from share.search import exceptions
from share.search.index_strategy.elastic8 import Elastic8IndexStrategy
from share.search import messages
from share.util import IDObfuscator
from share.util.checksum_iris import ChecksumIri


class Sharev2Elastic8IndexStrategy(Elastic8IndexStrategy):
    CURRENT_STRATEGY_CHECKSUM = ChecksumIri(
        checksumalgorithm_name='sha-256',
        salt='Sharev2Elastic8IndexStrategy',
        hexdigest='bcaa90e8fa8a772580040a8edbedb5f727202d1fca20866948bc0eb0e935e51f',
    )

    # abstract method from IndexStrategy
    @property
    def supported_message_types(self):
        return {
            messages.MessageType.INDEX_SUID,
            messages.MessageType.BACKFILL_SUID,
        }

    # abstract method from Elastic8IndexStrategy
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
                        'delimiter': '|',
                    }
                }
            }
        }

    # abstract method from Elastic8IndexStrategy
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
            'dynamic': False,
            'properties': {
                'affiliations': {'type': 'text', 'fields': exact_field},
                'contributors': {'type': 'text', 'fields': exact_field},
                'date': {'type': 'date', 'format': 'strict_date_optional_time'},
                'date_created': {'type': 'date', 'format': 'strict_date_optional_time'},
                'date_modified': {'type': 'date', 'format': 'strict_date_optional_time'},
                'date_published': {'type': 'date', 'format': 'strict_date_optional_time'},
                'date_updated': {'type': 'date', 'format': 'strict_date_optional_time'},
                'description': {'type': 'text'},
                'funders': {'type': 'text', 'fields': exact_field},
                'hosts': {'type': 'text', 'fields': exact_field},
                'id': {'type': 'keyword'},
                'identifiers': {'type': 'text', 'fields': exact_field},
                'justification': {'type': 'text'},
                'language': {'type': 'keyword'},
                'publishers': {'type': 'text', 'fields': exact_field},
                'registration_type': {'type': 'keyword'},
                'retracted': {'type': 'boolean'},
                'source_config': {'type': 'keyword'},
                'source_unique_id': {'type': 'keyword'},
                'sources': {'type': 'keyword'},
                'subjects': {'type': 'text', 'analyzer': 'subject_analyzer', 'search_analyzer': 'subject_search_analyzer'},
                'subject_synonyms': {'type': 'text', 'analyzer': 'subject_analyzer', 'search_analyzer': 'subject_search_analyzer', 'copy_to': 'subjects'},
                'tags': {'type': 'text', 'fields': exact_field},
                'title': {'type': 'text', 'fields': exact_field},
                'type': {'type': 'keyword'},
                'types': {'type': 'keyword'},
                'withdrawn': {'type': 'boolean'},
                'osf_related_resource_types': {'type': 'object', 'dynamic': True},
                'lists': {'type': 'object', 'dynamic': True},
            },
            'dynamic_templates': [
                {'exact_field_on_lists_strings': {'path_match': 'lists.*', 'match_mapping_type': 'string', 'mapping': {'type': 'text', 'fields': exact_field}}},
            ]
        }

    # abstract method from Elastic8IndexStrategy
    def build_elastic_actions(self, messages_chunk: messages.MessagesChunk):
        suid_ids = set(messages_chunk.target_ids_chunk)
        record_qs = db.FormattedMetadataRecord.objects.filter(
            suid_id__in=suid_ids,
            record_format='sharev2_elastic',
        )
        for record in record_qs:
            suid_ids.discard(record.suid_id)
            source_doc = json.loads(record.formatted_metadata)
            if source_doc.pop('is_deleted', False):
                yield self._build_delete_action(record.suid_id)
            else:
                yield self._build_index_action(record.suid_id, source_doc)
        # delete any that don't have the expected FormattedMetadataRecord
        for leftover_suid_id in suid_ids:
            yield self._build_delete_action(leftover_suid_id)

    # override Elastic8IndexStrategy
    def get_doc_id(self, message_target_id):
        return IDObfuscator.encode_id(message_target_id, db.SourceUniqueIdentifier)

    # override Elastic8IndexStrategy
    def get_message_target_id(self, doc_id):
        return IDObfuscator.decode_id(doc_id)

    def _build_index_action(self, target_id, source_doc):
        return {
            '_op_type': 'index',
            '_id': self.get_doc_id(target_id),
            '_source': source_doc,
        }

    def _build_delete_action(self, target_id):
        return {
            '_op_type': 'delete',
            '_id': self.get_doc_id(target_id),
        }

    class SpecificIndex(Elastic8IndexStrategy.SpecificIndex):
        # optional method from IndexStrategy.SpecificIndex
        def pls_handle_query__sharev2_backcompat(self, request_body=None, request_queryparams=None) -> dict:
            es8_request_body = {
                **(request_body or {}),
                'track_total_hits': True,
            }
            try:
                json_response = self.index_strategy.es8_client.search(
                    index=self.indexname,
                    # NOTE: the `body` param is deprecated; remove this backcompat method by ES9
                    body=es8_request_body,
                    params=request_queryparams or {},
                )
            except elasticsearch8.TransportError as error:
                raise exceptions.IndexStrategyError() from error  # TODO: error messaging
            try:  # mangle response for some limited backcompat with elasticsearch5
                json_response['hits']['total'] = json_response['hits']['total']['value']
            except KeyError:
                pass
            return json_response
