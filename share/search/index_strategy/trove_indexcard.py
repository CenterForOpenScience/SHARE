from share import models as db
from share.search.index_strategy.elastic8 import Elastic8IndexStrategy
from share.search.messages import MessageType
from share.search.search_request import (
    CardsearchParams,
    PropertysearchParams,
    ValuesearchParams,
)
from share.search.search_response import (
    CardsearchResponse,
    PropertysearchResponse,
    ValuesearchResponse,
)
from share.util import rdfutil, IDObfuscator


class UriAccumulator:  # TODO: move to an IndexcardDeriver
    def __init__(self):
        self.predicate_uris = set()
        self.reference_uris = set()
        self.vocab_uris = set()

    def add_triple(self, subj, pred, obj):
        self.add_reference(subj)
        self.add_predicate(pred)
        self.add_reference(obj)

    def add_predicate(self, uri):
        if isinstance(uri, rdflib.URIRef):
            self.predicate_uris.add(uri)
            self.add_vocab_for(uri)

    def add_reference(self, uri):
        if isinstance(uri, rdflib.URIRef):
            self.referenced_uris.add(uri)
            self.add_vocab_for(uri)

    def add_vocab_for(self, uri):
        # naive vocab recognition:
        # if the uri has a #fragment, assume everything before it is the vocab uri
        vocab, _, _ = uri.rpartition('#')
        if not vocab:
            # otherwise, assume everything before the last /path-segment
            vocab, _, _ = uri.rpartition('/')
        if '://' in vocab:
            self.vocab_uris.add(vocab)


class TroveV0IndexStrategy(Elastic8IndexStrategy):
    @property
    def supported_message_types(self):
        return {
            MessageType.INDEX_SUID,
            MessageType.BACKFILL_SUID,
        }

    @property
    def index_settings(self):
        return {}

    @property
    def index_mappings(self):
        return {
            'dynamic': 'strict',
            'properties': {
                'focus_iri': {
                    'type': 'keyword',
                },
                'vocab_iri': {
                    'type': 'keyword',
                },
                'predicate_iri': {
                    'type': 'keyword',
                },
                'referenced_iri': {
                    'type': 'keyword',
                },
            }
        }

    def _build_sourcedoc(self, indexcard):
        rdfgraph = rdflib.Graph().parse(data=record.formatted_metadata, format='turtle')
        accumulator = UriAccumulator()
        described_resource_uris = set()
        resource_uri = record.suid.described_resource_pid
        if resource_uri:
            resource_uri = rdfutil.normalize_pid_uri(resource_uri)
            described_resource_uris.add(resource_uri)
            for same_uri in rdfgraph.objects(resource_uri, rdflib.OWL.sameAs):
                described_resource_uris.add(same_uri)
        for triple in rdfgraph:
            accumulator.add_triple(*triple)
        return {
            'described_resource_uri': list(described_resource_uris),
            'vocab_uri': list(accumulator.vocab_uris),
            'predicate_uri': list(accumulator.predicate_uris),
            'referenced_uri': list(accumulator.reference_uris),
        }

    def build_elastic_actions(self, messages_chunk: messages.MessagesChunk):
        _suid_ids = set(messages_chunk.target_ids_chunk)
        for _suid_id, _serialized_doc in self._load_docs(suid_ids):
            suid_ids.discard(_suid_id)
            _source_doc = json.loads(_serialized_doc)
            if _source_doc.pop('is_deleted', False):
                yield self._build_delete_action(_suid_id)
            else:
                yield self._build_index_action(_suid_id, _source_doc)
        # delete any that don't have the expected card
        for _leftover_suid_id in suid_ids:
            yield self._build_delete_action(_leftover_suid_id)

    def build_action_generator(self, index_name, message_type):
        self.assert_message_type(message_type)

        def action_generator(target_id_chunk):
            remaining_suid_ids = set(target_id_chunk)
            record_qs = (
                db.FormattedMetadataRecord.objects
                .filter(suid_id__in=target_id_chunk, record_format='turtle')
                .select_related('suid')
            )
            for record in record_qs:
                action = {
                    '_index': index_name,
                    '_id': IDObfuscator.encode(record.suid),
                    '_op_type': 'index',
                    '_source': self._build_sourcedoc(record),
                }
                remaining_suid_ids.pop(record.suid_id)
                yield (record.suid_id, action)

            for suid_id in remaining_suid_ids:
                action = {
                    '_index': index_name,
                    '_type': 'metadata_record',
                    '_id': IDObfuscator.encode_id(suid_id, db.SourceUniqueIdentifier),
                    '_op_type': 'delete',
                }
                yield (suid_id, action)
        return action_generator

    class SpecificIndex(Elastic8IndexStrategy.SpecificIndex):
        def pls_handle_cardsearch(self, cardsearch_params: CardsearchParams) -> CardsearchResponse:
            raise NotImplementedError

        def pls_handle_propertysearch(self, propertysearch_params: PropertysearchParams) -> PropertysearchResponse:
            raise NotImplementedError

        def pls_handle_valuesearch(self, valuesearch_params: ValuesearchParams) -> ValuesearchResponse:
            raise NotImplementedError
