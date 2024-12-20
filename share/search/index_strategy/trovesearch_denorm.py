from __future__ import annotations
from collections import abc, defaultdict
import dataclasses
import functools
import json
import logging
import re
from typing import (
    Iterable,
    Iterator,
    Literal,
)

import celery
from django.conf import settings
import elasticsearch8
from primitive_metadata import primitive_rdf as rdf

from share.search import exceptions
from share.search import messages
from share.search.index_strategy.elastic8 import Elastic8IndexStrategy
from share.util.checksum_iri import ChecksumIri
from trove import models as trove_db
from trove.trovesearch.page_cursor import (
    MANY_MORE,
    OffsetCursor,
    PageCursor,
    ReproduciblyRandomSampleCursor,
)
from trove.trovesearch.search_params import (
    CardsearchParams,
    Propertypath,
    SearchFilter,
    Textsegment,
    ValueType,
    ValuesearchParams,
    is_globpath,
)
from trove.trovesearch.search_handle import (
    CardsearchHandle,
    CardsearchResult,
    PropertypathUsage,
    TextMatchEvidence,
    ValuesearchHandle,
    ValuesearchResult,
)
from trove.vocab import osfmap
from trove.vocab.namespaces import OWL, RDF
from . import _trovesearch_util as ts


logger = logging.getLogger(__name__)


class TrovesearchDenormIndexStrategy(Elastic8IndexStrategy):
    CURRENT_STRATEGY_CHECKSUM = ChecksumIri(
        checksumalgorithm_name='sha-256',
        salt='TrovesearchDenormIndexStrategy',
        hexdigest='8a87bb51d46af9794496e798f033e8ba1ea0251fa7a8ffa5d037e90fb0c602c8',
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
        return {
            'number_of_shards': 5,
            'number_of_replicas': 2,
        }

    # abstract method from Elastic8IndexStrategy
    def index_mappings(self):
        return {
            'dynamic': 'false',
            'dynamic_templates': self._dynamic_templates(),
            'properties': {
                'card': {'properties': self._card_mappings()},
                'iri_value': {'properties': self._iri_value_mappings()},
                'chunk_timestamp': {'type': 'unsigned_long'},
            },
        }

    def _dynamic_templates(self):
        return [
            {'dynamic_text_by_propertypath': {
                'path_match': '*.text_by_propertypath.*',
                'mapping': ts.TEXT_MAPPING,
            }},
            {'dynamic_text_by_depth': {
                'path_match': '*.text_by_depth.*',
                'mapping': ts.TEXT_MAPPING,
            }},
            {'dynamic_date_by_propertypath': {
                'path_match': '*.date_by_propertypath.*',
                'mapping': {
                    'type': 'date',
                    'format': 'strict_date_optional_time',
                },
            }},
            {'dynamic_int_by_propertypath': {
                'path_match': '*.int_by_propertypath.*',
                'mapping': {'type': 'long'},
            }},
        ]

    def _card_mappings(self):
        return {
            # simple keyword properties
            'card_iri': ts.KEYWORD_MAPPING,
            'card_pk': ts.KEYWORD_MAPPING,
            'suid': {
                'type': 'object',
                'properties': {
                    'source_config_label': ts.KEYWORD_MAPPING,
                    'source_record_identifier': ts.KEYWORD_MAPPING,
                },
            },
            **self._paths_and_values_mappings(),
        }

    def _iri_value_mappings(self):
        return {
            'value_name': ts.KEYWORD_MAPPING,
            'value_title': ts.KEYWORD_MAPPING,
            'value_label': ts.KEYWORD_MAPPING,
            'at_card_propertypaths': ts.KEYWORD_MAPPING,
            **self._paths_and_values_mappings(),
        }

    def _paths_and_values_mappings(self):
        return {
            'single_focus_iri': ts.KEYWORD_MAPPING,
            'focus_iri_synonyms': ts.KEYWORD_MAPPING,
            'propertypaths_present': ts.KEYWORD_MAPPING,
            # flattened properties (dynamic sub-properties with keyword values)
            'iri_by_propertypath': ts.FLATTENED_MAPPING,
            'iri_by_depth': ts.FLATTENED_MAPPING,
            # dynamic properties (see `_dynamic_templates`)
            'text_by_propertypath': {'type': 'object', 'dynamic': True},
            'text_by_depth': {'type': 'object', 'dynamic': True},
            'date_by_propertypath': {'type': 'object', 'dynamic': True},
            'int_by_propertypath': {'type': 'object', 'dynamic': True},
        }

    # override method from Elastic8IndexStrategy
    def after_chunk(self, messages_chunk: messages.MessagesChunk, indexnames: Iterable[str]):
        task__delete_iri_value_scraps.apply_async(
            kwargs={
                'index_strategy_name': self.name,
                'indexnames': list(indexnames),
                'card_pks': messages_chunk.target_ids_chunk,
                'timestamp': messages_chunk.timestamp,
            },
            countdown=settings.ELASTICSEARCH['POST_INDEX_DELAY'],
        )

    # abstract method from Elastic8IndexStrategy
    def build_elastic_actions(self, messages_chunk: messages.MessagesChunk):
        _indexcard_rdf_qs = ts.latest_rdf_for_indexcard_pks(messages_chunk.target_ids_chunk)
        _remaining_indexcard_pks = set(messages_chunk.target_ids_chunk)
        for _indexcard_rdf in _indexcard_rdf_qs:
            _docbuilder = self._SourcedocBuilder(_indexcard_rdf, messages_chunk.timestamp)
            if not _docbuilder.should_skip():  # if skipped, will be deleted
                _indexcard_pk = _indexcard_rdf.indexcard_id
                yield _indexcard_pk, (
                    self.build_index_action(
                        doc_id=_doc_id,
                        doc_source=_doc,
                    )
                    for _doc_id, _doc in _docbuilder.build_docs()
                )
                _remaining_indexcard_pks.discard(_indexcard_pk)
        # delete any that were skipped for any reason
        for _indexcard_pk in _remaining_indexcard_pks:
            yield _indexcard_pk, self.build_delete_action(_indexcard_pk)

    ###
    # implement abstract IndexStrategy.SpecificIndex

    class SpecificIndex(Elastic8IndexStrategy.SpecificIndex):

        # abstract method from IndexStrategy.SpecificIndex
        def pls_handle_search__sharev2_backcompat(self, request_body=None, request_queryparams=None) -> dict:
            return self.index_strategy.es8_client.search(
                index=self.indexname,
                body={
                    **(request_body or {}),
                    'track_total_hits': True,
                },
                params=(request_queryparams or {}),
            )

        # abstract method from IndexStrategy.SpecificIndex
        def pls_handle_cardsearch(self, cardsearch_params: CardsearchParams) -> CardsearchHandle:
            # cases to handle:
            # - sort by field value (streamable)
            # - sort by relevance to text (non-streamable)
            # - random sort (...non-streamable?)
            #   - first page (full random)
            #   - subsequent page (reproducibly randomm)
            # (for streaming pages, skip aggs and such on subsequents)
            # maybe start with a "header" request (no hits, minimal aggs)
            _querybuilder = _CardsearchQueryBuilder(cardsearch_params)
            _search_kwargs = _querybuilder.build()
            if settings.DEBUG:
                logger.info(json.dumps(_search_kwargs, indent=2))
            try:
                _es8_response = self.index_strategy.es8_client.search(
                    index=self.indexname,
                    source=False,  # no need to get _source, identifiers are enough
                    docvalue_fields=['card.card_iri'],
                    highlight={
                        'require_field_match': False,
                        'fields': {'card.text_by_propertypath.*': {}},
                    },
                    **_search_kwargs,
                )
            except elasticsearch8.TransportError as error:
                raise exceptions.IndexStrategyError() from error  # TODO: error messaging
            return self.index_strategy._cardsearch_handle(
                cardsearch_params,
                _es8_response,
                _querybuilder.response_cursor,
            )

        # abstract method from IndexStrategy.SpecificIndex
        def pls_handle_valuesearch(self, valuesearch_params: ValuesearchParams) -> ValuesearchHandle:
            _path = valuesearch_params.valuesearch_propertypath
            _cursor = OffsetCursor.from_cursor(valuesearch_params.page_cursor)
            _is_date_search = osfmap.is_date_property(_path[-1])
            _query = (
                _build_date_valuesearch(valuesearch_params)
                if _is_date_search
                else _build_iri_valuesearch(valuesearch_params, _cursor)
            )
            if settings.DEBUG:
                logger.info(json.dumps(_query, indent=2))
            try:
                _es8_response = self.index_strategy.es8_client.search(
                    **_query,
                    index=self.indexname,
                )
            except elasticsearch8.TransportError as error:
                raise exceptions.IndexStrategyError() from error  # TODO: error messaging
            return (
                self.index_strategy._valuesearch_dates_response(valuesearch_params, _es8_response)
                if _is_date_search
                else self.index_strategy._valuesearch_iris_response(valuesearch_params, _es8_response, _cursor)
            )

    ###
    # building sourcedocs

    @dataclasses.dataclass
    class _SourcedocBuilder:
        '''build elasticsearch sourcedocs for an rdf document
        '''
        indexcard_rdf: trove_db.IndexcardRdf
        chunk_timestamp: int
        indexcard: trove_db.Indexcard = dataclasses.field(init=False)
        focus_iri: str = dataclasses.field(init=False)
        rdfdoc: rdf.RdfTripleDictionary = dataclasses.field(init=False)

        def __post_init__(self) -> None:
            self.indexcard = self.indexcard_rdf.indexcard
            self.focus_iri = self.indexcard_rdf.focus_iri
            self.rdfdoc = self.indexcard_rdf.as_rdfdoc_with_supplements()

        def should_skip(self) -> bool:
            _suid = self.indexcard.source_record_suid
            return (
                # skip cards that belong to an obsolete suid with a later duplicate
                _suid.has_forecompat_replacement()
                # ...or that are without some value for name/title/label
                or not any(self.rdfdoc.q(self.focus_iri, osfmap.NAMELIKE_PROPERTIES))
            )

        def build_docs(self) -> Iterator[tuple[str, dict]]:
            # index once without `iri_value`
            yield self._doc_id(), {
                'card': self._card_subdoc,
                'chunk_timestamp': self.chunk_timestamp,
            }
            for _iri in self._fullwalk.paths_by_iri:
                yield self._doc_id(_iri), {
                    'card': self._card_subdoc,
                    'iri_value': self._iri_value_subdoc(_iri),
                    'chunk_timestamp': self.chunk_timestamp,
                }

        def _doc_id(self, value_iri=None) -> str:
            _card_pk = str(self.indexcard.pk)
            return (
                _card_pk
                if value_iri is None
                else f'{_card_pk}-{ts.b64(value_iri)}'
            )

        @functools.cached_property
        def _fullwalk(self) -> ts.GraphWalk:
            return ts.GraphWalk(self.rdfdoc, self.focus_iri)

        @functools.cached_property
        def _card_subdoc(self) -> dict:
            return {
                'card_iri': self.indexcard.get_iri(),
                'card_pk': str(self.indexcard.pk),
                'suid': {
                    'source_record_identifier': self.indexcard.source_record_suid.identifier,
                    'source_config_label': self.indexcard.source_record_suid.source_config.label,
                },
                **self._paths_and_values(self._fullwalk),
            }

        def _iri_value_subdoc(self, iri: str) -> dict:
            _shortwalk = self._fullwalk.shortwalk_from(iri)
            return {
                **self._paths_and_values(_shortwalk),
                'value_name': list(self._texts_at_properties(_shortwalk, osfmap.NAME_PROPERTIES)),
                'value_title': list(self._texts_at_properties(_shortwalk, osfmap.TITLE_PROPERTIES)),
                'value_label': list(self._texts_at_properties(_shortwalk, osfmap.LABEL_PROPERTIES)),
                'at_card_propertypaths': [
                    ts.propertypath_as_keyword(_path)
                    for _path in self._fullwalk.paths_by_iri[iri]
                ],
            }

        def _paths_and_values(self, walk: ts.GraphWalk):
            return {
                'single_focus_iri': walk.focus_iri.rstrip('/'),  # remove trailing slash, but keep the scheme
                'focus_iri_synonyms': ts.suffuniq_iris(ts.iri_synonyms(
                    walk.focus_iri,
                    self.rdfdoc,
                )),
                'propertypaths_present': self._propertypaths_present(walk),
                'iri_by_propertypath': self._iris_by_propertypath(walk),
                'iri_by_depth': self._iris_by_depth(walk),
                'text_by_propertypath': self._texts_by_propertypath(walk),
                'text_by_depth': self._texts_by_depth(walk),
                'date_by_propertypath': self._dates_by_propertypath(walk),
                'int_by_propertypath': self._ints_by_propertypath(walk),
            }

        def _propertypaths_present(self, walk: ts.GraphWalk):
            return [
                ts.propertypath_as_keyword(_path)
                for _path in walk.paths_walked
            ]

        def _iris_by_propertypath(self, walk: ts.GraphWalk):
            return {
                _path_field_name(_path): ts.suffuniq_iris(ts.iris_synonyms(_iris, self.rdfdoc))
                for _path, _iris in walk.iri_values.items()
            }

        def _iris_by_depth(self, walk: ts.GraphWalk):
            _by_depth: dict[int, set[str]] = defaultdict(set)
            for _path, _iris in walk.iri_values.items():
                _by_depth[len(_path)].update(_iris)
            return {
                _depth_field_name(_depth): ts.suffuniq_iris(ts.iris_synonyms(_iris, self.rdfdoc))
                for _depth, _iris in _by_depth.items()
            }

        def _texts_by_propertypath(self, walk: ts.GraphWalk):
            return {
                _path_field_name(_path): [_text.unicode_value for _text in _text_set]
                for _path, _text_set in walk.text_values.items()
            }

        def _texts_at_properties(self, walk: ts.GraphWalk, properties: Iterable[str]):
            for _property in properties:
                for _text_literal in walk.text_values.get((_property,), []):
                    yield _text_literal.unicode_value

        def _texts_by_depth(self, walk: ts.GraphWalk):
            _by_depth: dict[int, set[str]] = defaultdict(set)
            for _path, _text_set in walk.text_values.items():
                _by_depth[len(_path)].update(_text.unicode_value for _text in _text_set)
            return {
                _depth_field_name(_depth): list(_value_set)
                for _depth, _value_set in _by_depth.items()
            }

        def _dates_by_propertypath(self, walk: ts.GraphWalk):
            return {
                _path_field_name(_path): [
                    _date.isoformat()
                    for _date in _value_set
                ]
                for _path, _value_set in walk.date_values.items()
            }

        def _ints_by_propertypath(self, walk: ts.GraphWalk):
            return {
                _path_field_name(_path): list(_value_set)
                for _path, _value_set in walk.integer_values.items()
            }

    ###
    # normalizing search responses

    def _valuesearch_iris_response(
        self,
        valuesearch_params: ValuesearchParams,
        es8_response: dict,
        cursor: OffsetCursor,
    ) -> ValuesearchHandle:
        _iri_aggs = es8_response['aggregations'].get('agg_valuesearch_iris')
        _buckets = _iri_aggs['buckets']
        _bucket_count = len(_buckets)
        # WARNING: terribly hacky pagination (part two)
        _page_end_index = cursor.start_offset + cursor.bounded_page_size
        _bucket_page = _buckets[cursor.start_offset:_page_end_index]  # discard prior pages
        cursor.total_count = (
            MANY_MORE
            if (_bucket_count > _page_end_index)  # agg includes one more, if there
            else _bucket_count
        )
        return ValuesearchHandle(
            cursor=cursor,
            search_result_page=[
                self._valuesearch_iri_result(_iri_bucket)
                for _iri_bucket in _bucket_page
            ],
            search_params=valuesearch_params,
        )

    def _valuesearch_dates_response(
        self,
        valuesearch_params: ValuesearchParams,
        es8_response: dict,
    ) -> ValuesearchHandle:
        _year_buckets = (
            es8_response['aggregations']
            ['agg_valuesearch_dates']
            ['buckets']
        )
        return ValuesearchHandle(
            cursor=PageCursor(len(_year_buckets)),
            search_result_page=[
                self._valuesearch_date_result(_year_bucket)
                for _year_bucket in _year_buckets
            ],
            search_params=valuesearch_params,
        )

    def _valuesearch_iri_result(self, iri_bucket) -> ValuesearchResult:
        return ValuesearchResult(
            value_iri=iri_bucket['key'],
            value_type=_bucketlist(iri_bucket.get('agg_type_iri', [])),
            name_text=_bucketlist(iri_bucket.get('agg_value_name', [])),
            title_text=_bucketlist(iri_bucket.get('agg_value_title', [])),
            label_text=_bucketlist(iri_bucket.get('agg_value_label', [])),
            match_count=iri_bucket['doc_count'],
        )

    def _valuesearch_date_result(self, date_bucket) -> ValuesearchResult:
        return ValuesearchResult(
            value_iri=None,
            value_value=date_bucket['key_as_string'],
            label_text=(date_bucket['key_as_string'],),
            match_count=date_bucket['doc_count'],
        )

    def _cardsearch_handle(
        self,
        cardsearch_params: CardsearchParams,
        es8_response: dict,
        cursor: OffsetCursor,
    ) -> CardsearchHandle:
        _es8_total = es8_response['hits']['total']
        if _es8_total['relation'] != 'eq':
            cursor.total_count = MANY_MORE
        elif isinstance(cursor, ReproduciblyRandomSampleCursor) and not cursor.is_first_page():
            # account for the filtered-out first page
            cursor.total_count = _es8_total['value'] + len(cursor.first_page_ids)
        else:  # exact (and small) count
            cursor.total_count = _es8_total['value']
        _results = []
        for _es8_hit in es8_response['hits']['hits']:
            _card_iri = _es8_hit['fields']['card.card_iri'][0]
            _results.append(CardsearchResult(
                card_iri=_card_iri,
                card_pk=_es8_hit['_id'],
                text_match_evidence=list(self._gather_textmatch_evidence(_card_iri, _es8_hit)),
            ))
        _relatedproperty_list: list[PropertypathUsage] = []
        if cardsearch_params.related_property_paths:
            _relatedproperty_list.extend(
                PropertypathUsage(property_path=_path, usage_count=0)
                for _path in cardsearch_params.related_property_paths
            )
            _relatedproperty_by_pathkey = {
                ts.propertypath_as_keyword(_result.property_path): _result
                for _result in _relatedproperty_list
            }
            for _bucket in es8_response['aggregations']['agg_related_propertypath_usage']['buckets']:
                _relatedproperty_by_pathkey[_bucket['key']].usage_count += _bucket['doc_count']
        return CardsearchHandle(
            cursor=cursor,
            search_result_page=_results,
            related_propertypath_results=_relatedproperty_list,
            search_params=cardsearch_params,
        )

    def _gather_textmatch_evidence(self, card_iri, es8_hit) -> Iterator[TextMatchEvidence]:
        for _field, _snippets in es8_hit.get('highlight', {}).items():
            (_, _, _encoded_path) = _field.rpartition('.')
            _property_path = _parse_path_field_name(_encoded_path)
            for _snippet in _snippets:
                yield TextMatchEvidence(
                    property_path=_property_path,
                    matching_highlight=rdf.literal(_snippet),
                    card_iri=card_iri,
                )


###
# building queries

@dataclasses.dataclass
class _BoolBuilder:
    bool_innards: dict[str, list[dict]] = dataclasses.field(
        default_factory=lambda: {
            'filter': [],
            'must_not': [],
            'must': [],
            'should': [],
        },
    )

    def as_query(self):
        return {'bool': self.bool_innards}

    def add_boolpart(self, key: str, query: dict) -> None:
        self.bool_innards[key].append(query)

    def add_boolparts(self, boolparts: Iterator[tuple[str, dict]]):
        for _key, _query in boolparts:
            self.add_boolpart(_key, _query)


@dataclasses.dataclass
class _QueryHelper:
    base_field: Literal['card', 'iri_value']
    textsegment_set: frozenset[Textsegment]
    filter_set: frozenset[SearchFilter]
    relevance_matters: bool

    def boolparts(self) -> Iterator[tuple[str, dict]]:
        yield from self.iri_boolparts()
        yield from self.text_boolparts()

    def iri_boolparts(self) -> Iterator[tuple[str, dict]]:
        # iri-keyword filters
        for _searchfilter in self.filter_set:
            if _searchfilter.operator == SearchFilter.FilterOperator.NONE_OF:
                yield 'must_not', self._iri_filter(_searchfilter)
            elif _searchfilter.operator == SearchFilter.FilterOperator.ANY_OF:
                yield 'filter', self._iri_filter(_searchfilter)
            elif _searchfilter.operator == SearchFilter.FilterOperator.IS_PRESENT:
                yield 'filter', self._presence_query(_searchfilter)
            elif _searchfilter.operator == SearchFilter.FilterOperator.IS_ABSENT:
                yield 'must_not', self._presence_query(_searchfilter)
            elif _searchfilter.operator.is_date_operator():
                yield 'filter', self._date_filter(_searchfilter)
            else:
                raise ValueError(f'unknown filter operator {_searchfilter.operator}')

    def text_boolparts(self) -> Iterator[tuple[str, dict]]:
        # text-based queries
        for _textsegment in self.textsegment_set:
            if _textsegment.is_negated:
                yield 'must_not', self._exact_text_query(_textsegment)
            elif not _textsegment.is_fuzzy:
                yield 'must', self._exact_text_query(_textsegment)
            else:
                yield 'must', self._fuzzy_text_must_query(_textsegment)
                if self.relevance_matters:
                    yield 'should', self._fuzzy_text_should_query(_textsegment)

    def _presence_query(self, search_filter) -> dict:
        return _any_query([
            self._path_presence_query(_path)
            for _path in search_filter.propertypath_set
        ])

    def _path_presence_query(self, path: Propertypath):
        _field = f'{self.base_field}.propertypaths_present'
        return {'term': {_field: ts.propertypath_as_keyword(path)}}

    def _iri_filter(self, search_filter) -> dict:
        _iris = ts.suffuniq_iris(search_filter.value_set)
        return _any_query([
            self._path_iri_query(_path, _iris)
            for _path in search_filter.propertypath_set
        ])

    def _path_iri_query(self, path, suffuniq_iris):
        if path == (OWL.sameAs,):
            _field = f'{self.base_field}.focus_iri_synonyms'
        elif is_globpath(path):
            _field = f'{self.base_field}.iri_by_depth.{_depth_field_name(len(path))}'
        else:
            _field = f'{self.base_field}.iri_by_propertypath.{_path_field_name(path)}'
        return {'terms': {_field: suffuniq_iris}}

    def _date_filter(self, search_filter):
        return _any_query([
            self._date_filter_for_path(_path, search_filter.operator, search_filter.value_set)
            for _path in search_filter.propertypath_set
        ])

    def _date_filter_for_path(self, path, filter_operator, value_set):
        _field = f'{self.base_field}.date_by_propertypath.{_path_field_name(path)}'
        if filter_operator == SearchFilter.FilterOperator.BEFORE:
            _value = min(value_set)  # rely on string-comparable isoformat
            return {'range': {_field: {'lt': _daterange_value(_value)}}}
        elif filter_operator == SearchFilter.FilterOperator.AFTER:
            _value = max(value_set)  # rely on string-comparable isoformat
            return {'range': {_field: {'gt': _daterange_value(_value)}}}
        elif filter_operator == SearchFilter.FilterOperator.AT_DATE:
            return _any_query([
                {'range': {_field: {'gte': _filtervalue, 'lte': _filtervalue}}}
                for _filtervalue in map(_daterange_value, value_set)
            ])
        else:
            raise ValueError(f'invalid date filter operator (got {filter_operator})')

    def _text_field_name(self, propertypath: Propertypath):
        return (
            f'{self.base_field}.text_by_depth.{_depth_field_name(len(propertypath))}'
            if is_globpath(propertypath)
            else f'{self.base_field}.text_by_propertypath.{_path_field_name(propertypath)}'
        )

    def _exact_text_query(self, textsegment: Textsegment) -> dict:
        # TODO: textsegment.is_openended (prefix query)
        return _any_query([
            {'match_phrase': {self._text_field_name(_path): {'query': textsegment.text}}}
            for _path in textsegment.propertypath_set
        ])

    def _fuzzy_text_must_query(self, textsegment: Textsegment) -> dict:
        # TODO: textsegment.is_openended (prefix query)
        return _any_query([
            {'match': {
                self._text_field_name(_path): {
                    'query': textsegment.text,
                    'fuzziness': 'AUTO',
                    # TODO: consider 'operator': 'and' (by query param FilterOperator, `cardSearchText[*][every-word]=...`)
                },
            }}
            for _path in textsegment.propertypath_set
        ])

    def _fuzzy_text_should_query(self, textsegment: Textsegment):
        _slop = len(textsegment.text.split())
        return _any_query([
            {'match_phrase': {
                self._text_field_name(_path): {'query': textsegment.text, 'slop': _slop},
            }}
            for _path in textsegment.propertypath_set
        ])


@dataclasses.dataclass
class _CardsearchQueryBuilder:
    params: CardsearchParams

    def build(self):
        return {
            'query': self._cardsearch_query(),
            'aggs': self._cardsearch_aggs(),
            'sort': list(self._cardsearch_sorts()) or None,
            'from_': self._cardsearch_start_offset(),
            'size': self.response_cursor.bounded_page_size,
        }

    @functools.cached_property
    def response_cursor(self) -> OffsetCursor:
        _request_cursor = self.params.page_cursor
        if (
            _request_cursor.is_basic()
            and not self.params.sort_list
            and not self.params.cardsearch_textsegment_set
        ):
            return ReproduciblyRandomSampleCursor.from_cursor(_request_cursor)
        return OffsetCursor.from_cursor(_request_cursor)

    def _cardsearch_start_offset(self):
        if (
            self.response_cursor.is_first_page()
            or not isinstance(self.response_cursor, ReproduciblyRandomSampleCursor)
        ):
            return self.response_cursor.start_offset
        return self.response_cursor.start_offset - len(self.response_cursor.first_page_ids)

    def _cardsearch_query(self) -> dict:
        _bool = _BoolBuilder()
        _bool.add_boolparts(
            _QueryHelper(
                base_field='card',
                textsegment_set=self.params.cardsearch_textsegment_set,
                filter_set=self.params.cardsearch_filter_set,
                relevance_matters=(not self.params.sort_list),
            ).boolparts(),
        )
        # exclude iri_value docs (possible optimization: separate indexes)
        _bool.add_boolpart('must_not', {'exists': {'field': 'iri_value'}})
        return (
            self._randomly_ordered_query(_bool)
            if isinstance(self.response_cursor, ReproduciblyRandomSampleCursor)
            else _bool.as_query()
        )

    def _randomly_ordered_query(self, _bool: _BoolBuilder) -> dict:
        assert isinstance(self.response_cursor, ReproduciblyRandomSampleCursor)
        if not self.response_cursor.first_page_ids:
            # independent random sample
            return {
                'function_score': {
                    'query': _bool.as_query(),
                    'boost_mode': 'replace',
                    'random_score': {},  # default random_score is fast and unpredictable
                },
            }
        _firstpage_filter = {'terms': {'card.card_pk': self.response_cursor.first_page_ids}}
        if self.response_cursor.is_first_page():
            # returning to a first page previously visited
            _bool.add_boolpart('filter', _firstpage_filter)
            return _bool.as_query()
        # get a subsequent page using reproducible randomness
        _bool.add_boolpart('must_not', _firstpage_filter)
        return {
            'function_score': {
                'query': _bool.as_query(),
                'boost_mode': 'replace',
                'random_score': {
                    'seed': ''.join(self.response_cursor.first_page_ids),
                    'field': 'card.card_pk',
                },
            },
        }

    def _cardsearch_aggs(self):
        _aggs = {}
        if self.params.related_property_paths:
            _aggs['agg_related_propertypath_usage'] = {'terms': {
                'field': 'card.propertypaths_present',
                'include': [
                    ts.propertypath_as_keyword(_path)
                    for _path in self.params.related_property_paths
                ],
                'size': len(self.params.related_property_paths),
            }}
        return _aggs

    def _cardsearch_sorts(self):
        for _sortparam in self.params.sort_list:
            _fieldkey = _path_field_name(_sortparam.propertypath)
            if _sortparam.value_type == ValueType.DATE:
                _field = f'card.date_by_propertypath.{_fieldkey}'
                _unmapped_type = 'date'
            elif _sortparam.value_type == ValueType.INTEGER:
                _field = f'card.int_by_propertypath.{_fieldkey}'
                _unmapped_type = 'long'
            else:
                raise ValueError(f'unsupported sort value type: {_sortparam}')
            yield {_field: {
                'order': 'desc' if _sortparam.descending else 'asc',
                'unmapped_type': _unmapped_type,
            }}


def _build_iri_valuesearch(params: ValuesearchParams, cursor: OffsetCursor) -> dict:
    _path = params.valuesearch_propertypath
    _bool = _BoolBuilder()
    _bool.add_boolpart('filter', {'term': {
        'iri_value.at_card_propertypaths': ts.propertypath_as_keyword(_path),
    }})
    _bool.add_boolparts(
        _QueryHelper(
            base_field='card',
            textsegment_set=params.cardsearch_textsegment_set,
            filter_set=params.cardsearch_filter_set,
            relevance_matters=False,
        ).boolparts(),
    )
    _bool.add_boolparts(
        _QueryHelper(
            base_field='iri_value',
            textsegment_set=params.valuesearch_textsegment_set,
            filter_set=params.valuesearch_filter_set,
            relevance_matters=False,
        ).boolparts()
    )
    return {
        'query': _bool.as_query(),
        'size': 0,  # ignore hits; just want the aggs
        'aggs': {
            'agg_valuesearch_iris': {
                'terms': {
                    'field': 'iri_value.single_focus_iri',
                    # WARNING: terribly hacky pagination (part one)
                    'size': cursor.start_offset + cursor.bounded_page_size + 1,
                },
                'aggs': {
                    'agg_type_iri': {'terms': {
                        'field': f'iri_value.iri_by_propertypath.{_path_field_name((RDF.type,))}',
                    }},
                    'agg_value_name': {'terms': {'field': 'iri_value.value_name'}},
                    'agg_value_title': {'terms': {'field': 'iri_value.value_title'}},
                    'agg_value_label': {'terms': {'field': 'iri_value.value_label'}},
                },
            },
        },
    }


def _build_date_valuesearch(params: ValuesearchParams) -> dict:
    assert not params.valuesearch_textsegment_set
    assert not params.valuesearch_filter_set
    _bool = _BoolBuilder()
    _bool.add_boolparts(
        _QueryHelper(
            base_field='card',
            textsegment_set=params.cardsearch_textsegment_set,
            filter_set=params.cardsearch_filter_set,
            relevance_matters=False,
        ).boolparts(),
    )
    # exclude iri_value docs (possible optimization: separate indexes)
    _bool.add_boolpart('must_not', {'exists': {'field': 'iri_value'}})
    _field = f'card.date_by_propertypath.{_path_field_name(params.valuesearch_propertypath)}'
    return {
        'query': _bool.as_query(),
        'size': 0,  # ignore hits; just want the aggs
        'aggs': {'agg_valuesearch_dates': {
            'date_histogram': {
                'field': _field,
                'calendar_interval': 'year',
                'format': 'yyyy',
                'order': {'_key': 'desc'},
                'min_doc_count': 1,
            },
        }}
    }


###
# assorted helper functions

def _bucketlist(agg_result: dict) -> list[str]:
    return [
        _bucket['key']
        for _bucket in agg_result['buckets']
    ]


def _daterange_value(datevalue: str):
    _cleanvalue = datevalue.strip()
    if re.fullmatch(r'\d{4,}', _cleanvalue):
        return f'{_cleanvalue}||/y'
    if re.fullmatch(r'\d{4,}-\d{2}', _cleanvalue):
        return f'{_cleanvalue}||/M'
    if re.fullmatch(r'\d{4,}-\d{2}-\d{2}', _cleanvalue):
        return f'{_cleanvalue}||/d'
    raise ValueError(f'bad date value "{datevalue}"')


def _depth_field_name(depth: int) -> str:
    return f'depth{depth}'


def _path_field_name(path: Propertypath) -> str:
    return ts.b64(ts.propertypath_as_keyword(path))


def _parse_path_field_name(path_field_name: str) -> Propertypath:
    # inverse of _path_field_name
    _list = json.loads(ts.b64_reverse(path_field_name))
    assert isinstance(_list, list)
    assert all(isinstance(_item, str) for _item in _list)
    return tuple(_list)


def _any_query(queries: abc.Collection[dict]):
    if len(queries) == 1:
        (_query,) = queries
        return _query
    return {'bool': {'should': list(queries), 'minimum_should_match': 1}}


@celery.shared_task(
    name='share.search.index_strategy.trovesearch_denorm.task__delete_iri_value_scraps',
    max_retries=None,  # retries only on delete_by_query conflicts -- should work eventually!
    retry_backoff=True,
    bind=True,  # for explicit retry
)
def task__delete_iri_value_scraps(
    task: celery.Task,
    index_strategy_name: str,
    card_pks: list[int],
    indexnames: list[str],
    timestamp: int,
):
    '''followup task to delete value-docs no longer present

    each time an index-card is updated, value-docs are created (or updated) for each iri value
    present in the card's contents -- if some values are absent from a later update, the
    corresponding docs will remain untouched

    this task deletes those untouched value-docs after the index has refreshed at its own pace
    (allowing a slightly longer delay for items to _stop_ matching queries for removed values)
    '''
    from share.search.index_strategy import get_index_strategy
    _index_strategy = get_index_strategy(index_strategy_name)
    assert isinstance(_index_strategy, Elastic8IndexStrategy)
    # delete any docs that belong to cards in this chunk but weren't touched by indexing
    _delete_resp = _index_strategy.es8_client.delete_by_query(
        index=indexnames,
        query={'bool': {'must': [
            {'terms': {'card.card_pk': card_pks}},
            {'range': {'chunk_timestamp': {'lt': timestamp}}},
        ]}},
        params={
            'slices': 'auto',
            'conflicts': 'proceed',  # count conflicts instead of halting
            'request_cache': False,
        },
    )
    _conflict_count = _delete_resp.get('version_conflicts', 0)
    if _conflict_count > 0:
        raise task.retry()
