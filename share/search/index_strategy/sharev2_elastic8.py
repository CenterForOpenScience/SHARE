import json
import logging
import typing

from django.db.models import F
import elasticsearch8

from share.models import (
    FeatureFlag,
    FormattedMetadataRecord,
    SourceUniqueIdentifier,
)
from share.search import exceptions
from share.search import messages
from share.search.index_strategy.elastic8 import Elastic8IndexStrategy
from share.util import IDObfuscator
from share.util.checksum_iri import ChecksumIri
from trove.models import DerivedIndexcard, ResourceIdentifier
from trove.vocab.namespaces import SHAREv2


logger = logging.getLogger(__name__)


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
        _suid_ids = set(messages_chunk.target_ids_chunk)
        for _suid_id, _serialized_doc in self._load_docs(_suid_ids):
            _doc_id = self._get_doc_id(_suid_id)
            _suid_ids.discard(_suid_id)
            _source_doc = json.loads(_serialized_doc)
            if _source_doc.pop('is_deleted', False):
                yield _suid_id, self.build_delete_action(_doc_id)
            else:
                yield _suid_id, self.build_index_action(_doc_id, _source_doc)
        # delete any that don't have the expected card
        for _leftover_suid_id in _suid_ids:
            yield _leftover_suid_id, self.build_delete_action(self._get_doc_id(_leftover_suid_id))

    def _get_doc_id(self, suid_id: int):
        return IDObfuscator.encode_id(suid_id, SourceUniqueIdentifier)

    def _load_docs(self, suid_ids) -> typing.Iterable[tuple[int, str]]:
        _card_qs = (
            DerivedIndexcard.objects
            .filter(upriver_indexcard__source_record_suid_id__in=suid_ids)
            .filter(deriver_identifier__in=ResourceIdentifier.objects.queryset_for_iri(SHAREv2.sharev2_elastic))
            .annotate(suid_id=F('upriver_indexcard__source_record_suid_id'))
        )
        if FeatureFlag.objects.flag_is_up(FeatureFlag.IGNORE_SHAREV2_INGEST):
            for _card in _card_qs:
                yield (_card.suid_id, _card.derived_text)
        else:  # draw from both DerivedIndexcard and FormattedMetadataRecord
            _remaining_suids = set(suid_ids)
            for _card in _card_qs:
                yield (_card.suid_id, _card.derived_text)
                _remaining_suids.discard(_card.suid_id)
            _record_qs = FormattedMetadataRecord.objects.filter(
                suid_id__in=_remaining_suids,
                record_format='sharev2_elastic',
            )
            for _record in _record_qs:
                yield (_record.suid_id, _record.formatted_metadata)

    class SpecificIndex(Elastic8IndexStrategy.SpecificIndex):
        # optional method from IndexStrategy.SpecificIndex
        def pls_handle_search__sharev2_backcompat(self, request_body=None, request_queryparams=None) -> dict:
            try:
                json_response = self.index_strategy.es8_client.search(
                    index=self.indexname,
                    body=(request_body or {}),
                    params=(request_queryparams or {}),
                    track_total_hits=True,
                )
            except elasticsearch8.TransportError as error:
                raise exceptions.IndexStrategyError() from error  # TODO: error messaging
            try:  # mangle response for some limited backcompat with elasticsearch5
                es8_total = json_response['hits']['total']
                json_response['hits']['total'] = es8_total['value']
                json_response['hits']['_total'] = es8_total
            except KeyError:
                pass
            return json_response
