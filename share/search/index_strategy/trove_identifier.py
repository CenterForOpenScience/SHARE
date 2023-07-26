import logging

import elasticsearch8

from share.search.index_strategy._base import IndexStrategy
from share.search.index_strategy._util import path_as_keyword
from share.search.index_strategy.elastic8 import Elastic8IndexStrategy
from share.search import exceptions
from share.search import messages
from share.search.search_request import (
    PropertysearchParams,
    ValuesearchParams,
    Textsegment,
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
        hexdigest='1311c394e2058d9784cc5dbb3a3de4d73be2c2cc795d06ca44289510849977a7',
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
                # TODO 'namespace_iri': {'type': 'keyword'}, (via rdfs:isDefinedIn, maybe)
                'used_for_property': {'type': 'keyword'},
                'used_for_propertypath_from_focus': {'type': 'keyword'},
                'used_for_propertypath_from_any_subject': {'type': 'keyword'},
                # TODO: make usage counts available for weighting
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
        _identifier_usage = indexcard_index.get_identifier_usage_as_value(identifier)
        if not _identifier_usage:
            return None
        return {
            'iri': _identifier_usage['iri'],
            'used_for_property': _identifier_usage['for_property'],
            'used_for_propertypath_from_focus': _identifier_usage['for_path_from_focus'],
            'used_for_propertypath_from_any_subject': _identifier_usage['for_path_from_any_subject'],
            'namelike_text': _identifier_usage['namelike_text'],
            'related_text': _identifier_usage['related_text'],
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
            _doc_id = _identifier.sufficiently_unique_iri
            _sourcedoc = self._build_sourcedoc(_indexcard_index, _identifier)
            _index_action = (
                self.build_index_action(doc_id=_doc_id, doc_source=_sourcedoc)
                if _sourcedoc
                else self.build_delete_action(doc_id=_doc_id)
            )
            yield _identifier.id, _index_action
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
                    query=self._valuesearch_query(valuesearch_params),
                    size=0,  # ignore cardsearch hits; just want the aggs
                    # aggs=self._valuesearch_aggs(valuesearch_params),
                    # TODO: highlight?
                )
                return dict(_es8_response)
            except elasticsearch8.TransportError as error:
                raise exceptions.IndexStrategyError() from error  # TODO: error messaging
            return self._valuesearch_response(valuesearch_params, _es8_response)

        def pls_handle_propertysearch(self, propertysearch_params: PropertysearchParams) -> PropertysearchResponse:
            raise NotImplementedError

        ###
        # query implementation

        def _valuesearch_query(self, valuesearch_params: ValuesearchParams):
            _bool_query = {
                'filter': [{'term': {
                    'used_for_propertypath_from_focus': path_as_keyword(valuesearch_params.valuesearch_property_path),
                }}],
                'must': [],
                'must_not': [],
                'should': [],
            }
            # TODO: valuesearch_filter_set
            _fuzzysegments = []
            for _textsegment in valuesearch_params.valuesearch_textsegment_set:
                if _textsegment.is_negated:
                    _bool_query['must_not'].append(self._excluded_text_query(_textsegment))
                elif _textsegment.is_fuzzy:
                    _fuzzysegments.append(_textsegment)
                else:
                    _bool_query['must'].append(self._exact_text_query(_textsegment))
            if _fuzzysegments:
                _bool_query['must'].append(self._fuzzy_text_must_query(_fuzzysegments))
                # _bool_query['should'].extend(self._fuzzy_text_should_queries(_fuzzysegments))
            return {'bool': _bool_query}

        def _valuesearch_aggs(valuesearch_params: ValuesearchParams):
            raise NotImplementedError  # TODO

        def _valuesearch_response(valuesearch_params, es8_response):
            raise NotImplementedError  # TODO

        def _excluded_text_query(self, textsegment: Textsegment) -> dict:
            return {'match_phrase': {
                'namelike_text': {
                    'query': textsegment.text,
                },
            }}

        def _exact_text_query(self, textsegment: Textsegment) -> dict:
            # TODO: textsegment.is_openended (prefix query)
            return {'match_phrase': {
                'namelike_text': {
                    'query': textsegment.text,
                },
            }}

        def _fuzzy_text_must_query(self, textsegments: list[Textsegment]) -> dict:
            # TODO: textsegment.is_openended (prefix query)
            return {'multi_match': {
                'fields': ['namelike_text', 'related_text'],
                'query': ' '.join(
                    _textsegment.text
                    for _textsegment in textsegments
                ),
                'fuzziness': 'AUTO',
            }}
