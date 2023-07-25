import logging

import elasticsearch8

from share.search.index_strategy._base import IndexStrategy
from share.search.index_strategy.elastic8 import Elastic8IndexStrategy
from share.search import exceptions
from share.search import messages
from share.search.search_request import (
    PropertysearchParams,
    ValuesearchParams,
)
from share.search.search_response import (
    PropertysearchResponse,
    ValuesearchResponse,
)
from share.util.checksum_iri import ChecksumIri
from trove import models as trove_db


logger = logging.getLogger(__name__)


class TroveIdentifierIndexStrategy(Elastic8IndexStrategy):
    CURRENT_STRATEGY_CHECKSUM = ChecksumIri(
        checksumalgorithm_name='sha-256',
        salt='TroveIdentifierIndexStrategy',
        hexdigest='714fc7ae3c81ddf473c63a90b8d4d0be6828d479766a16a747b2ff658da78622',
    )

    @property
    def supported_message_types(self):
        return {
            messages.MessageType.IDENTIFIER_INDEXED,
            messages.MessageType.BACKFILL_IDENTIFIER,
        }

    # abstract method from IndexStrategy
    @property
    def backfill_phases(self):
        return [messages.MessageType.BACKFILL_IDENTIFIER]

    def index_settings(self):
        return {}

    def index_mappings(self):
        return {
            'dynamic': 'false',
            'properties': {
                'iri': {'type': 'keyword'},
                'is_value_for_property': {'type': 'keyword'},
                'is_value_for_propertypath_from_focus': {'type': 'keyword'},
                'is_value_for_propertypath_from_any_subject': {'type': 'keyword'},
                # TODO:
                # 'namespace_iri': {'type': 'keyword'},
                # 'rank_by_property': {'type': 'rank_features'},
                # 'rank_by_propertypath_from_focus': {'type': 'rank_features'},
                # 'rank_by_propertypath_from_any_subject': {'type': 'rank_features'},
                'namelike_text': {
                    'type': 'text',
                    'fields': {
                        'raw': {'type': 'keyword'},
                    },
                },
                'related_text': {
                    'type': 'text',
                    'fields': {
                        'raw': {'type': 'keyword'},
                    },
                },
            },
        }

    def _build_sourcedoc(self, indexcard_index: IndexStrategy.SpecificIndex, identifier: trove_db.ResourceIdentifier):
        _identifier_usage = indexcard_index.get_identifier_value_usage(identifier)
        return {
            'iri': _identifier_usage['iri'],
            'is_value_for_property': list(_identifier_usage['count_for_property'].keys()),
            'is_value_for_propertypath_from_focus': list(_identifier_usage['count_for_path_from_focus'].keys()),
            'is_value_for_propertypath_from_any_subject': list(_identifier_usage['count_for_path_from_any_subject'].keys()),
            # TODO: (without dots in feature names)
            # 'rank_by_property': _identifier_usage['count_for_property'],
            # 'rank_by_propertypath_from_focus': _identifier_usage['count_for_path_from_focus'],
            # 'rank_by_propertypath_from_any_subject': _identifier_usage['count_for_path_from_any_subject'],
            # TODO: use counts for text relevance
            'namelike_text': list(_identifier_usage['count_for_namelike_text'].keys()),
            'related_text': list(_identifier_usage['count_for_related_text'].keys()),
        }

    def build_elastic_actions(self, messages_chunk: messages.MessagesChunk):
        _identifier_qs = (
            trove_db.ResourceIdentifier.objects
            .filter(id__in=messages_chunk.target_ids_chunk)
            .prefetch_related('indexcard_set')
        )
        _remaining_identifier_ids = set(messages_chunk.target_ids_chunk)
        _indexcard_index = IndexStrategy.get_by_name('trove_indexcard').pls_get_default_for_searching()
        for _identifier in _identifier_qs:
            _remaining_identifier_ids.discard(_identifier.id)
            _index_action = self.build_index_action(
                doc_id=_identifier.sufficiently_unique_iri,
                doc_source=self._build_sourcedoc(_indexcard_index, _identifier),
            )
            yield _identifier.id, _index_action
        # delete any that don't have any of the expected card
        _leftovers = (
            trove_db.ResourceIdentifier.objects
            .filter(id__in=_remaining_identifier_ids)
            .values_list('id', 'sufficiently_unique_iri')
        )
        for _id, _doc_id in _leftovers:
            yield _id, self.build_delete_action(_doc_id)

    class SpecificIndex(Elastic8IndexStrategy.SpecificIndex):
        def pls_handle_search__sharev2_backcompat(self, request_body=None, request_queryparams=None) -> dict:
            return self.index_strategy.es8_client.search(
                index=self.indexname,
                body={
                    **(request_body or {}),
                    'track_total_hits': True,
                },
                params=(request_queryparams or {}),
            )

        def pls_handle_valuesearch(self, valuesearch_params: ValuesearchParams) -> ValuesearchResponse:
            try:
                _es8_response = self.index_strategy.es8_client.search(
                    index=self.indexname,
                    query=_valuesearch_query(valuesearch_params),
                    size=0,  # ignore cardsearch hits; just want the aggs
                    aggs=_valuesearch_aggs(valuesearch_params),
                )
            except elasticsearch8.TransportError as error:
                raise exceptions.IndexStrategyError() from error  # TODO: error messaging
            return _valuesearch_response(valuesearch_params, _es8_response)

        def pls_handle_propertysearch(self, propertysearch_params: PropertysearchParams) -> PropertysearchResponse:
            raise NotImplementedError


###
# module-local functions

def _valuesearch_query(valuesearch_params: ValuesearchParams):
    raise NotImplementedError  # TODO


def _valuesearch_aggs(valuesearch_params: ValuesearchParams):
    raise NotImplementedError  # TODO


def _valuesearch_response(valuesearch_params, es8_response):
    raise NotImplementedError  # TODO
