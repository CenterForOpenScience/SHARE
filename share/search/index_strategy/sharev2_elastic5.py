from __future__ import annotations
import functools
import json
import logging

from django.conf import settings
import elasticsearch5
import elasticsearch5.helpers

from share.models import SourceUniqueIdentifier
from share.search import exceptions, messages
from share.search.index_status import IndexStatus
from share.search.index_strategy._base import IndexStrategy
from share.search.index_strategy._util import timestamp_to_readable_datetime
from share.util import IDObfuscator
from share.util.checksum_iri import ChecksumIri
from trove import models as trove_db
from trove.vocab.namespaces import SHAREv2


logger = logging.getLogger(__name__)


def get_doc_id(suid_id):
    return IDObfuscator.encode_id(suid_id, SourceUniqueIdentifier)


# using a static, single-index strategy to represent the existing "share_postrend_backcompat"
# search index in elastic5, with intent to put new work in elastic8+ and drop elastic5 soon.
# (see share.search.index_strategy.sharev2_elastic8 for this same index in elastic8)
class Sharev2Elastic5IndexStrategy(IndexStrategy):
    CURRENT_STRATEGY_CHECKSUM = ChecksumIri(
        checksumalgorithm_name='sha-256',
        salt='Sharev2Elastic5IndexStrategy',
        hexdigest='7b6620bfafd291489e2cfea7e645b8311c2485a3012e467abfee4103f7539cc4',
    )
    STATIC_INDEXNAME = 'share_postrend_backcompat'

    # perpetuated optimizations from times long past
    MAX_CHUNK_BYTES = 10 * 1024 ** 2  # 10 megs

    @classmethod
    @functools.cache
    def _get_elastic5_client(cls) -> elasticsearch5.Elasticsearch:
        should_sniff = settings.ELASTICSEARCH['SNIFF']
        return elasticsearch5.Elasticsearch(
            settings.ELASTICSEARCH5_URL,
            retry_on_timeout=True,
            timeout=settings.ELASTICSEARCH['TIMEOUT'],
            # sniff before doing anything
            sniff_on_start=should_sniff,
            # refresh nodes after a node fails to respond
            sniff_on_connection_fail=should_sniff,
            # and also every 60 seconds
            sniffer_timeout=60 if should_sniff else None,
        )

    @property
    def es5_client(self):
        return self._get_elastic5_client()  # cached classmethod for shared client

    @property
    def single_index(self) -> IndexStrategy.SpecificIndex:
        return self.get_index(self.STATIC_INDEXNAME)

    # abstract method from IndexStrategy
    @classmethod
    def each_index_subname(self):
        yield self.STATIC_INDEXNAME

    # override IndexStrategy
    @property
    def nonurgent_messagequeue_name(self):
        return 'es-share-postrend-backcompat'

    # override IndexStrategy
    @property
    def urgent_messagequeue_name(self):
        return f'{self.nonurgent_messagequeue_name}.urgent'

    # override IndexStrategy
    @property
    def indexname_prefix(self):
        return self.STATIC_INDEXNAME

    # abstract method from IndexStrategy
    def compute_strategy_checksum(self):
        return ChecksumIri.digest_json(
            'sha-256',
            salt=self.__class__.__name__,
            raw_json={
                'indexname': self.STATIC_INDEXNAME,
                'mappings': self._index_mappings(),
                'settings': self._index_settings(),
            }
        )

    # abstract method from IndexStrategy
    def pls_make_default_for_searching(self):
        pass  # the one index is the only one

    # abstract method from IndexStrategy
    def pls_get_default_for_searching(self):
        return self

    # abstract method from IndexStrategy
    def each_existing_index(self, *args, **kwargs):
        _index = self.single_index
        if _index.pls_check_exists():
            yield _index

    # abstract method from IndexStrategy
    def each_live_index(self, *args, **kwargs):
        yield self.single_index

    # abstract method from IndexStrategy
    def each_subnamed_index(self):
        yield self.single_index

    # abstract method from IndexStrategy
    def pls_handle_messages_chunk(self, messages_chunk):
        logger.debug('got messages_chunk %s', messages_chunk)
        self.assert_message_type(messages_chunk.message_type)
        bulk_stream = elasticsearch5.helpers.streaming_bulk(
            self.es5_client,
            self._build_elastic_actions(messages_chunk),
            max_chunk_bytes=self.MAX_CHUNK_BYTES,
            raise_on_error=False,
        )
        for (ok, response) in bulk_stream:
            op_type, response_body = next(iter(response.items()))
            message_target_id = self._get_message_target_id(response_body['_id'])
            is_done = ok or (op_type == 'delete' and response_body.get('status') == 404)
            error_text = None if is_done else str(response_body)
            yield messages.IndexMessageResponse(
                is_done=is_done,
                index_message=messages.IndexMessage(messages_chunk.message_type, message_target_id),
                status_code=response_body.get('status'),
                error_text=error_text,
            )

    # abstract method from IndexStrategy
    @property
    def supported_message_types(self):
        return {
            messages.MessageType.INDEX_SUID,
            messages.MessageType.BACKFILL_SUID,
        }

    # abstract method from IndexStrategy
    @property
    def backfill_message_type(self):
        return messages.MessageType.BACKFILL_SUID

    def _index_settings(self):
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
                        'delimiter': '|',
                    }
                }
            }
        }

    def _index_mappings(self):
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

    def _get_message_target_id(self, doc_id):
        return IDObfuscator.decode_id(doc_id)

    def _build_elastic_actions(self, messages_chunk):
        action_template = {
            '_index': self.STATIC_INDEXNAME,
            '_type': 'creativeworks',
        }
        suid_ids = set(messages_chunk.target_ids_chunk)
        _derived_qs = (
            trove_db.DerivedIndexcard.objects
            .filter(upriver_indexcard__source_record_suid_id=suid_ids)
            .filter(deriver_identifier__in=(
                trove_db.ResourceIdentifier.objects
                .queryset_for_iri(SHAREv2.sharev2_elastic)
            ))
            .select_related('upriver_indexcard')
        )
        for _derived_card in _derived_qs:
            _suid_id = _derived_card.upriver_indexcard.source_record_suid_id
            doc_id = get_doc_id(_suid_id)
            suid_ids.remove(_suid_id)
            source_doc = json.loads(_derived_card.derived_text)
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
            logger.debug('built action for suid_id=%s: %s', _suid_id, action)
            yield action
        # delete any that don't have the expected DerivedIndexcard
        for leftover_suid_id in suid_ids:
            logger.debug('deleting suid_id=%s', leftover_suid_id)
            action = {
                **action_template,
                '_id': get_doc_id(leftover_suid_id),
                '_op_type': 'delete',
            }
            yield action

    # optional method from IndexStrategy
    def pls_handle_search__passthru(self, request_body=None, request_queryparams=None) -> dict:
        '''the definitive sharev2-search api: passthru to elasticsearch version 5
        '''
        if request_queryparams:
            request_queryparams.pop('indexStrategy', None)
        try:
            return self.es5_client.search(
                index=self.STATIC_INDEXNAME,
                body=request_body or {},
                params=request_queryparams or {},
            )
        except elasticsearch5.TransportError as error:
            raise exceptions.IndexStrategyError() from error  # TODO: error messaging

    class SpecificIndex(IndexStrategy.SpecificIndex):
        index_strategy: Sharev2Elastic5IndexStrategy  # narrow type

        # override IndexStrategy.SpecificIndex
        @property
        def full_index_name(self):
            return self.index_strategy.STATIC_INDEXNAME

        # abstract method from IndexStrategy.SpecificIndex
        def pls_create(self):
            # check index exists (if not, create)
            logger.debug('Ensuring index %s', self.full_index_name)
            indices_api = self.index_strategy.es5_client.indices
            if not indices_api.exists(index=self.full_index_name):
                indices_api.create(
                    self.full_index_name,
                    body={
                        'settings': self.index_strategy._index_settings(),
                        'mappings': self.index_strategy._index_mappings(),
                    },
                )
            self.pls_refresh()
            logger.debug('Waiting for yellow status')
            (
                self.index_strategy.es5_client.cluster
                .health(wait_for_status='yellow')
            )
            logger.info('Finished setting up Elasticsearch index %s', self.full_index_name)

        # abstract method from IndexStrategy.SpecificIndex
        def pls_start_keeping_live(self):
            pass  # there is just the one index, always kept live

        # abstract method from IndexStrategy.SpecificIndex
        def pls_stop_keeping_live(self):
            raise exceptions.IndexStrategyError(
                f'{self.__class__.__qualname__} is implemented for only one index, '
                f'"{self.full_index_name}", which is always kept live (until elasticsearch5 '
                'support is dropped)'
            )

        # abstract method from IndexStrategy.SpecificIndex
        def pls_refresh(self):
            (
                self.index_strategy.es5_client.indices
                .refresh(index=self.full_index_name)
            )
            logger.info('Refreshed index %s', self.full_index_name)

        # abstract method from IndexStrategy.SpecificIndex
        def pls_delete(self):
            logger.warning(f'{self.__class__.__name__}: deleting index {self.full_index_name}')
            (
                self.index_strategy.es5_client.indices
                .delete(index=self.full_index_name, ignore=[400, 404])
            )

        # abstract method from IndexStrategy.SpecificIndex
        def pls_check_exists(self):
            return bool(
                self.index_strategy.es5_client.indices
                .exists(index=self.full_index_name)
            )

        # abstract method from IndexStrategy.SpecificIndex
        def pls_get_status(self) -> IndexStatus:
            try:
                stats = (
                    self.index_strategy.es5_client.indices
                    .stats(index=self.full_index_name, metric='docs')
                )
                existing_indexes = (
                    self.index_strategy.es5_client.indices
                    .get_settings(index=self.full_index_name, name='index.creation_date')
                )
                index_settings = existing_indexes[self.full_index_name]
                index_stats = stats['indices'][self.full_index_name]
            except (KeyError, elasticsearch5.exceptions.NotFoundError):
                # not yet created
                return IndexStatus(
                    index_subname=self.subname,
                    specific_indexname=self.full_index_name,
                    is_kept_live=False,
                    is_default_for_searching=False,
                    creation_date='',
                    doc_count=0,
                )
            return IndexStatus(
                index_subname=self.subname,
                specific_indexname=self.full_index_name,
                is_kept_live=True,
                is_default_for_searching=True,
                creation_date=timestamp_to_readable_datetime(
                    index_settings['settings']['index']['creation_date'],
                ),
                doc_count=index_stats['primaries']['docs']['count'],
            )
