import rdflib

from share import models as db
from share.search.index_setup.base import IndexSetup
from share.search.messages import MessageType
from share.util import rdfutil, IDObfuscator


class UriAccumulator:
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
        # assume everything before #fragment, if it's there
        vocab, _, _ = uri.rpartition('#')
        if not vocab:
            # otherwise, assume everything before the last /path-segment
            vocab, _, _ = uri.rpartition('/')
        if '://' in vocab:
            self.vocab_uris.add(vocab)


class TroveV0IndexSetup(IndexSetup):
    @property
    def supported_message_types(self):
        return {MessageType.INDEX_SUID}

    @property
    def index_settings(self):
        return {}

    @property
    def index_mappings(self):
        return {
            'metadata_record': {
                'dynamic': 'strict',
                'properties': {
                    'normalized_datum_id': {
                        'type': 'keyword',
                    },
                    'described_resource_uri': {
                        'type': 'keyword',
                    },
                    'vocab_uri': {
                        'type': 'keyword',
                    },
                    'predicate_uri': {
                        'type': 'keyword',
                    },
                    'referenced_uri': {
                        'type': 'keyword',
                    },
                }
            }
        }

    def _build_sourcedoc(self, record):
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
                    '_type': 'metadata_record',
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
                    'id': IDObfuscator.encode_id(suid_id, db.SourceUniqueIdentifier),
                    '_op_type': 'delete',
                }
                yield (suid_id, action)
        return action_generator
