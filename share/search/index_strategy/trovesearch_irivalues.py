import typing

from share.search import messages
from share.search.index_strategy.elastic8 import Elastic8IndexStrategy
from share.util.checksum_iri import ChecksumIri
from . import _trovesearch_util as ts


class TrovesearchMentionsIndexStrategy(Elastic8IndexStrategy):
    CURRENT_STRATEGY_CHECKSUM = ChecksumIri(
        checksumalgorithm_name='sha-256',
        salt='TrovesearchMentionsIndexStrategy',
        hexdigest='...',
    )

    # abstract method from IndexStrategy
    @property
    def supported_message_types(self):
        return {
            messages.MessageType.UPDATE_INDEXCARD,
            messages.MessageType.BACKFILL_INDEXCARD,
        }

    # abstract method from IndexStrategy
    @property
    def backfill_message_type(self):
        return messages.MessageType.BACKFILL_INDEXCARD

    # abstract method from Elastic8IndexStrategy
    def index_settings(self):
        return {}

    # abstract method from Elastic8IndexStrategy
    def index_mappings(self):
        return {
            'dynamic': 'false',
            'properties': {
                'iri': ts.IRI_KEYWORD_MAPPING,  # include sameAs
                'indexcard_iri': ts.KEYWORD_MAPPING,
                'indexcard_pk': ts.KEYWORD_MAPPING,
                'propertypath_from_focus': ts.KEYWORD_MAPPING,
                'depth_from_focus': ts.KEYWORD_MAPPING,
                # flattened properties (dynamic sub-properties with keyword values)
                'iri_by_relative_propertypath': ts.FLATTENED_MAPPING,
                'iri_by_relative_depth': ts.FLATTENED_MAPPING,
                # dynamic properties (see dynamic_templates, below)
                'dynamics': {
                    'type': 'object',
                    'properties': {
                        'text_by_relative_propertypath': {'type': 'object', 'dynamic': True},
                        'text_by_relative_depth': {'type': 'object', 'dynamic': True},
                        'date_by_relative_propertypath': {'type': 'object', 'dynamic': True},
                    },
                },
            },
            'dynamic_templates': [
                {'dynamic_text_by_path': {
                    'path_match': 'dynamics.text_by_relative_propertypath.*',
                    'mapping': ts.TEXT_MAPPING,
                }},
                {'dynamic_text_by_depth': {
                    'path_match': 'dynamics.text_by_relative_depth.*',
                    'mapping': ts.TEXT_MAPPING,
                }},
                {'dynamic_date': {
                    'path_match': 'dynamics.date_by_relative_propertypath.*',
                    'mapping': {
                        'type': 'date',
                        'format': 'strict_date_optional_time',
                    },
                }},
            ],
        }

    def before_chunk(self, messages_chunk: messages.MessagesChunk, indexnames: typing.Iterable[str]):
        if messages_chunk.message_type in (
            messages.MessageType.UPDATE_INDEXCARD,
            messages.MessageType.BACKFILL_INDEXCARD,
        ):
            self.es8_client.delete_by_query(
                index=list(indexnames),
                query={'terms': {'indexcard_pk': messages_chunk.target_ids_chunk}},
            )

    # abstract method from Elastic8IndexStrategy
    def build_elastic_actions(self, messages_chunk: messages.MessagesChunk):
        _indexcard_rdf_qs = ts.latest_rdf_for_indexcard_pks(messages_chunk.target_ids_chunk)
        for _indexcard_rdf in _indexcard_rdf_qs:
            for _doc_id, _iri_usage_doc in self._build_iri_usage_docs(_indexcard_rdf):
                _index_action = self.build_index_action(_doc_id, _iri_usage_doc)

    def _build_iri_usage_docs(self, indexcard_rdf: trove_db.IndexcardRdf):
        _graphwalk = ts.GraphWalk(
            rdf.RdfGraph(_indexcard_rdf.as_rdf_tripledict()),
            _indexcard_rdf.focus_iri,
        )
        # TODO: skip iris already in a static thesaurus
        ...

