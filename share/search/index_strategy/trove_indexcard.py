from collections import defaultdict
import contextlib
import copy
import dataclasses
import datetime
import json
import logging
import uuid
from typing import Iterable, Optional

import elasticsearch8
from gather import primitive_rdf

from share.search.index_strategy.elastic8 import Elastic8IndexStrategy
from share.search import exceptions
from share.search import messages
from share.search.search_request import (
    CardsearchParams,
    PropertysearchParams,
    ValuesearchParams,
    SearchFilter,
    Textsegment,
    SortParam,
)
from share.search.search_response import (
    CardsearchResponse,
    PropertysearchResponse,
    ValuesearchResponse,
    TextMatchEvidence,
    CardsearchResult,
    ValuesearchResult,
)
from share.util.checksum_iri import ChecksumIri
from trove import models as trove_db
from trove.util.iris import get_sufficiently_unique_iri, is_worthwhile_iri, iri_path_as_keyword
from trove.vocab.osfmap import is_date_property
from trove.vocab.namespaces import TROVE, FOAF, RDF, RDFS, DCTERMS, OWL


logger = logging.getLogger(__name__)


class TroveIndexcardIndexStrategy(Elastic8IndexStrategy):
    CURRENT_STRATEGY_CHECKSUM = ChecksumIri(
        checksumalgorithm_name='sha-256',
        salt='TroveIndexcardIndexStrategy',
        hexdigest='8064751bfbf58eb0b4299e617833fb049f1c35df3a6dd4357405c5c9fd263317',
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
    def backfill_phases(self):
        return [
            messages.MessageType.BACKFILL_INDEXCARD,
        ]

    def index_settings(self):
        return {}

    def index_mappings(self):
        _capped_keyword = {
            'type': 'keyword',
            'ignore_above': 8191,  # ignore keyword terms that exceed reach lucene's internal limit
            # see https://www.elastic.co/guide/en/elasticsearch/reference/current/ignore-above.html
        }
        _common_nested_keywords = {
            'path_from_focus': _capped_keyword,
            'property_iri': _capped_keyword,
            'nearest_subject_iri': _capped_keyword,
            'nearest_subject_suffuniq_iri': _capped_keyword,
            'path_from_nearest_subject': _capped_keyword,
        }
        return {
            'dynamic': 'false',
            'properties': {
                'focus_iri': _capped_keyword,
                'suffuniq_focus_iri': _capped_keyword,
                'nested_iri': {
                    'type': 'nested',  # TODO: consider 'flattened' field for simple iri-matching
                    'dynamic': 'false',
                    'properties': {
                        **_common_nested_keywords,
                        'iri_value': _capped_keyword,
                        'suffuniq_iri_value': _capped_keyword,
                        'value_type_iri': _capped_keyword,
                        'value_name_text': {
                            'type': 'text',
                            'fields': {'raw': _capped_keyword},
                            'copy_to': 'value_namelike_text',
                        },
                        'value_title_text': {
                            'type': 'text',
                            'fields': {'raw': _capped_keyword},
                            'copy_to': 'value_namelike_text',
                        },
                        'value_label_text': {
                            'type': 'text',
                            'fields': {'raw': _capped_keyword},
                            'copy_to': 'value_namelike_text',
                        },
                        'value_namelike_text': {'type': 'text'},
                    },
                },
                'nested_date': {
                    'type': 'nested',
                    'dynamic': 'false',
                    'properties': {
                        **_common_nested_keywords,
                        'date_value': {
                            'type': 'date',
                            'format': 'strict_date_optional_time',
                        },
                    },
                },
                'nested_text': {
                    'type': 'nested',
                    'dynamic': 'false',
                    'properties': {
                        **_common_nested_keywords,
                        'language_iri': _capped_keyword,
                        'text_value': {
                            'type': 'text',
                            'index_options': 'offsets',  # for faster highlighting
                            'store': True,  # avoid loading _source to render highlights
                            'fields': {'raw': _capped_keyword},
                        },
                    },
                },
            },
        }

    def _build_sourcedoc(self, indexcard_rdf):
        _rdfdoc = primitive_rdf.TripledictWrapper(indexcard_rdf.as_rdf_tripledict())
        _nested_iris = defaultdict(set)
        _nested_dates = defaultdict(set)
        _nested_texts = defaultdict(set)
        for _walk_pathkey, _walk_obj in _PredicatePathWalker(_rdfdoc.tripledict).walk_from_subject(indexcard_rdf.focus_iri):
            if isinstance(_walk_obj, str):
                _nested_iris[_walk_pathkey].add(_walk_obj)
            elif isinstance(_walk_obj, datetime.date):
                _nested_dates[_walk_pathkey].add(datetime.date.isoformat(_walk_obj))
            elif is_date_property(_walk_pathkey.last_predicate_iri):
                _nested_dates[_walk_pathkey].add(_walk_obj.unicode_text)
            elif isinstance(_walk_obj, primitive_rdf.Text):
                _nested_texts[(_walk_pathkey, _walk_obj.language_iri)].add(_walk_obj.unicode_text)
        _focus_iris = {indexcard_rdf.focus_iri}
        _suffuniq_focus_iris = {get_sufficiently_unique_iri(indexcard_rdf.focus_iri)}
        for _identifier in indexcard_rdf.indexcard.focus_identifier_set.all():
            _focus_iris.update(_identifier.raw_iri_list)
            _suffuniq_focus_iris.add(_identifier.sufficiently_unique_iri)
        return {
            'focus_iri': list(_focus_iris),
            'suffuniq_focus_iri': list(_suffuniq_focus_iris),
            'nested_iri': [
                self._iri_nested_sourcedoc(_pathkey, _iri, _rdfdoc)
                for _pathkey, _value_set in _nested_iris.items()
                for _iri in _value_set
                if is_worthwhile_iri(_iri)
            ],
            'nested_date': [
                {
                    **_pathkey.as_nested_keywords(),
                    'date_value': list(_value_set),
                }
                for _pathkey, _value_set in _nested_dates.items()
            ],
            'nested_text': [
                {
                    **_pathkey.as_nested_keywords(),
                    'language_iri': _language_iri,
                    'text_value': list(_value_set),
                }
                for (_pathkey, _language_iri), _value_set in _nested_texts.items()
            ],
        }

    def _iri_nested_sourcedoc(self, pathkey, iri, rdfdoc):
        _iris = [
            iri,
            *rdfdoc.q(iri, OWL.sameAs),
        ]
        _sourcedoc = {
            **pathkey.as_nested_keywords(),
            'iri_value': _iris,
            'suffuniq_iri_value': [
                get_sufficiently_unique_iri(_iri)
                for _iri in _iris
            ],
            'value_type_iri': list(rdfdoc.q(iri, RDF.type)),
            # TODO: don't discard language for name/title/label
            'value_name_text': [
                _text.unicode_text
                for _text in rdfdoc.q(iri, FOAF.name)
                if isinstance(_text, primitive_rdf.Text)
            ],
            'value_title_text': [
                _text.unicode_text
                for _text in rdfdoc.q(iri, DCTERMS.title)
                if isinstance(_text, primitive_rdf.Text)
            ],
            'value_label_text': [
                _text.unicode_text
                for _text in rdfdoc.q(iri, RDFS.label)
                if isinstance(_text, primitive_rdf.Text)
            ],
        }
        return _sourcedoc

    def build_elastic_actions(self, messages_chunk: messages.MessagesChunk):
        _indexcard_rdf_qs = (
            trove_db.LatestIndexcardRdf.objects
            .filter(indexcard_id__in=messages_chunk.target_ids_chunk)
            .select_related('indexcard')
            .prefetch_related('indexcard__focus_identifier_set')
        )
        _remaining_indexcard_ids = set(messages_chunk.target_ids_chunk)
        for _indexcard_rdf in _indexcard_rdf_qs:
            _indexcard_id = _indexcard_rdf.indexcard_id
            _remaining_indexcard_ids.discard(_indexcard_id)
            _index_action = self.build_index_action(
                doc_id=_indexcard_rdf.indexcard.get_iri(),
                doc_source=self._build_sourcedoc(_indexcard_rdf),
            )
            yield _indexcard_id, _index_action
        # delete any that don't have "latest" rdf
        _leftovers = trove_db.Indexcard.objects.filter(id__in=_remaining_indexcard_ids)
        for _indexcard in _leftovers:
            yield _indexcard.id, self.build_delete_action(_indexcard.get_iri())

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

        def pls_handle_cardsearch(self, cardsearch_params: CardsearchParams) -> CardsearchResponse:
            try:
                _es8_response = self.index_strategy.es8_client.search(
                    index=self.indexname,
                    query=self._cardsearch_query(
                        cardsearch_params.cardsearch_filter_set,
                        cardsearch_params.cardsearch_textsegment_set,
                    ),
                    sort=self._cardsearch_sort(cardsearch_params.sort),
                    source=False,  # no need to get _source; _id is enough
                )
            except elasticsearch8.TransportError as error:
                raise exceptions.IndexStrategyError() from error  # TODO: error messaging
            return self._cardsearch_response(cardsearch_params, _es8_response)

        def pls_handle_valuesearch(self, valuesearch_params: ValuesearchParams) -> ValuesearchResponse:
            try:
                _es8_response = self.index_strategy.es8_client.search(
                    index=self.indexname,
                    query=self._cardsearch_query(
                        valuesearch_params.cardsearch_filter_set,
                        valuesearch_params.cardsearch_textsegment_set,
                        additional_filters=[{'nested': {
                            'path': 'nested_iri',
                            'query': {'term': {'nested_iri.path_from_focus': iri_path_as_keyword(
                                valuesearch_params.valuesearch_property_path,
                            )}},
                        }}],
                    ),
                    size=0,  # ignore cardsearch hits; just want the aggs
                    aggs=self._valuesearch_aggs(valuesearch_params),
                )
            except elasticsearch8.TransportError as error:
                raise exceptions.IndexStrategyError() from error  # TODO: error messaging
            return self._valuesearch_response(valuesearch_params, _es8_response)

        def pls_handle_propertysearch(self, propertysearch_params: PropertysearchParams) -> PropertysearchResponse:
            # _propertycard_filter = SearchFilter(
            #     property_path=(RDF.type,),
            #     value_set=frozenset([RDF.Property]),
            #     operator=SearchFilter.FilterOperator.ANY_OF,
            # )
            raise NotImplementedError('TODO: just static PropertysearchResponse somewhere')

        def get_identifier_usage_as_value(self, identifier: trove_db.ResourceIdentifier) -> Optional[dict]:
            _filter_cards_with_identifier = {'nested': {
                'path': 'nested_iri',
                'query': {'term': {
                    'nested_iri.suffuniq_iri_value': identifier.sufficiently_unique_iri,
                }},
            }}
            _identifier_usage_agg = {
                'in_nested_iri': {
                    'nested': {'path': 'nested_iri'},
                    'aggs': {
                        'with_iri': {
                            'filter': {'term': {
                                'nested_iri.suffuniq_iri_value': identifier.sufficiently_unique_iri,
                            }},
                            'aggs': {
                                'exact_iri_value': {'terms': {
                                    'field': 'nested_iri.iri_value',
                                    'size': 100,
                                }},
                                'for_property': {'terms': {
                                    'field': 'nested_iri.property_iri',
                                    'size': 100,
                                }},
                                'for_path_from_focus': {'terms': {
                                    'field': 'nested_iri.path_from_focus',
                                    'size': 100,
                                }},
                                'for_path_from_any_subject': {'terms': {
                                    'field': 'nested_iri.path_from_nearest_subject',
                                    'size': 100,
                                }},
                            },
                        },
                    },
                },
                'in_nested_text': {
                    'nested': {'path': 'nested_text'},
                    'aggs': {
                        'about_iri': {
                            'filter': {'term': {
                                'nested_text.nearest_subject_suffuniq_iri': identifier.sufficiently_unique_iri,
                            }},
                            'aggs': {
                                'related_text': {'terms': {
                                    'field': 'nested_text.text_value.raw',
                                    'size': 100,
                                }},
                                'namelike_text_properties': {
                                    'filter': {'terms': {
                                        'nested_text.path_from_nearest_subject': [
                                            iri_path_as_keyword([_iri])
                                            for _iri in (FOAF.name, RDFS.label, DCTERMS.title)
                                        ],
                                    }},
                                    'aggs': {
                                        'namelike_text': {'terms': {
                                            'field': 'nested_text.text_value.raw',
                                            'size': 100,
                                        }},
                                    },
                                },
                            },
                        },
                    },
                },
            }
            try:
                _es8_response = self.index_strategy.es8_client.search(
                    index=self.indexname,
                    query=_filter_cards_with_identifier,
                    size=0,  # ignore cardsearch hits; just want the aggs
                    aggs=_identifier_usage_agg,
                )
            except elasticsearch8.TransportError as error:
                raise exceptions.IndexStrategyError() from error  # TODO: error messaging
            if not _es8_response['hits']['total']['value']:
                return None
            _iri_results = _es8_response['aggregations']['in_nested_iri']['with_iri']
            _text_results = _es8_response['aggregations']['in_nested_text']['about_iri']
            return {
                # TODO: include bucket counts
                'iri': _bucketlist(_iri_results['exact_iri_value']),
                'for_property': _bucketlist(_iri_results['for_property']),
                'for_path_from_focus': _bucketlist(_iri_results['for_path_from_focus']),
                'for_path_from_any_subject': _bucketlist(_iri_results['for_path_from_any_subject']),
                'namelike_text': _bucketlist(_text_results['namelike_text_properties']['namelike_text']),
                'related_text': _bucketlist(_text_results['related_text']),
            }

        ###
        # query implementation

        def _cardsearch_query(
            self,
            filter_set, textsegment_set, *,
            additional_filters=None,
            relevance_matters=True,
        ) -> dict:
            _bool_query = {
                'filter': additional_filters or [],
                'must': [],
                'must_not': [],
                'should': [],
            }
            for _searchfilter in filter_set:
                if _searchfilter.operator == SearchFilter.FilterOperator.NONE_OF:
                    _bool_query['must_not'].append(self._cardsearch_iri_filter(_searchfilter))
                elif _searchfilter.operator == SearchFilter.FilterOperator.ANY_OF:
                    _bool_query['filter'].append(self._cardsearch_iri_filter(_searchfilter))
                elif _searchfilter.operator.is_date_operator():
                    _bool_query['filter'].append(self._cardsearch_date_filter(_searchfilter))
                else:
                    raise ValueError(f'unknown filter operator {_searchfilter.operator}')
            _textq_builder = self._TextQueryBuilder('nested_text.text_value', nested_path='nested_text', inner_hits=self._cardsearch_inner_hits())
            for _boolkey, _textquery in _textq_builder.textsegment_queries(textsegment_set, relevance_matters=relevance_matters):
                _bool_query[_boolkey].append(_textquery)
            return {'bool': _bool_query}

        def _cardsearch_inner_hits(self, *, highlight_query=None) -> dict:
            _highlight = {
                'type': 'unified',
                'fields': {'nested_text.text_value': {}},
            }
            if highlight_query is not None:
                _highlight['highlight_query'] = highlight_query
            return {
                'name': str(uuid.uuid4()),  # avoid inner-hit name collisions
                'highlight': _highlight,
                '_source': False,  # _source is expensive for nested docs
                'docvalue_fields': [
                    'nested_text.path_from_focus',
                    'nested_text.language_iri',
                ],
            }

        def _valuesearch_aggs(self, valuesearch_params: ValuesearchParams):
            # TODO: valuesearch_filter_set (just rdf:type => nested_iri.value_type_iri)
            _nested_iri_bool = {
                'filter': [{'term': {'nested_iri.path_from_focus': iri_path_as_keyword(
                    valuesearch_params.valuesearch_property_path,
                )}}],
                'must': [],
                'must_not': [],
                'should': [],
            }
            _textq_builder = self._TextQueryBuilder('nested_iri.value_namelike_text')
            for _boolkey, _textquery in _textq_builder.textsegment_queries(valuesearch_params.valuesearch_textsegment_set):
                _nested_iri_bool[_boolkey].append(_textquery)
            _aggs = {
                'in_nested_iri': {
                    'nested': {'path': 'nested_iri'},
                    'aggs': {
                        'value_at_propertypath': {
                            'filter': {'bool': _nested_iri_bool},
                            'aggs': {
                                'iri_values': {
                                    'terms': {
                                        'field': 'nested_iri.iri_value',
                                        'size': 13,
                                        # TODO: pagination
                                    },
                                    'aggs': {
                                        'type_iri': {'terms': {
                                            'field': 'nested_iri.value_type_iri',
                                        }},
                                        'name_text': {'terms': {
                                            'field': 'nested_iri.value_name_text.raw',
                                        }},
                                        'title_text': {'terms': {
                                            'field': 'nested_iri.value_title_text.raw',
                                        }},
                                        'label_text': {'terms': {
                                            'field': 'nested_iri.value_label_text.raw',
                                        }},
                                    },
                                },
                            },
                        },
                    },
                },
            }
            _aggs['without_cardsearch'] = {
                'global': {},
                'aggs': copy.deepcopy(_aggs)
            }
            return _aggs

        def _valuesearch_response(self, valuesearch_params, es8_response):
            _result_list = []
            _result_by_iri = {}
            _matched_aggs = es8_response['aggregations']['in_nested_iri']
            _match_buckets = _matched_aggs['value_at_propertypath']['iri_values']['buckets']
            for _iri_bucket in _match_buckets:
                _result = self._valuesearch_result(_iri_bucket)
                _result.match_count = _iri_bucket['doc_count']
                _result_by_iri[_iri_bucket['key']] = _result
                _result_list.append(_result)
            _unmatched_aggs = es8_response['aggregations']['without_cardsearch']['in_nested_iri']
            _nonmatch_buckets = _unmatched_aggs['value_at_propertypath']['iri_values']['buckets']
            for _iri_bucket in _nonmatch_buckets:
                _iri = _iri_bucket['key']
                try:
                    _result = _result_by_iri[_iri]
                except KeyError:
                    _result = self._valuesearch_result(_iri_bucket)
                    _result_list.append(_result)
                _result.total_count = _iri_bucket['doc_count']
            return ValuesearchResponse(search_result_page=_result_list)

        def _valuesearch_result(self, iri_bucket):
            return ValuesearchResult(
                value_iri=iri_bucket['key'],
                value_type=_bucketlist(iri_bucket['type_iri']),
                name_text=_bucketlist(iri_bucket['name_text']),
                title_text=_bucketlist(iri_bucket['title_text']),
                label_text=_bucketlist(iri_bucket['label_text']),
            )

        def _cardsearch_iri_filter(self, search_filter) -> dict:
            _propertypath_keyword = iri_path_as_keyword(search_filter.property_path)
            return {'nested': {
                'path': 'nested_iri',
                'query': {'bool': {
                    'filter': [
                        {'term': {'nested_iri.path_from_focus': _propertypath_keyword}},
                        {'terms': {'nested_iri.suffuniq_iri_value': [
                            get_sufficiently_unique_iri(_iri)
                            for _iri in search_filter.value_set
                        ]}},
                    ],
                }},
            }}

        def _cardsearch_date_filter(self, search_filter) -> dict:
            if search_filter.operator == SearchFilter.FilterOperator.BEFORE:
                _range_op = 'lt'
                _value = min(search_filter.value_set)  # rely on string-comparable isoformat
            elif search_filter.operator == SearchFilter.FilterOperator.AFTER:
                _range_op = 'gte'
                _value = max(search_filter.value_set)  # rely on string-comparable isoformat
            else:
                raise ValueError(f'invalid date filter operator (got {search_filter.operator})')
            _date_value = datetime.datetime.fromisoformat(_value).date()
            _propertypath_keyword = iri_path_as_keyword(search_filter.property_path)
            return {'nested': {
                'path': 'nested_date',
                'query': {'bool': {
                    'filter': [
                        {'term': {'nested_date.path_from_focus': _propertypath_keyword}},
                        {'range': {'nested_date.date_value': {
                            _range_op: f'{_date_value}||/d',  # round to the day
                        }}},
                    ],
                }},
            }}

        def _cardsearch_sort(self, sort: tuple[SortParam]):
            return [
                {'nested_date.date_value': {
                    'order': ('desc' if _sortparam.descending else 'asc'),
                    'nested': {
                        'path': 'nested_date',
                        'filter': {'term': {
                            'nested_date.path_from_focus': iri_path_as_keyword([_sortparam.property_iri]),
                        }},
                    },
                }}
                for _sortparam in sort
            ]

        def _cardsearch_response(self, cardsearch_params, es8_response) -> CardsearchResponse:
            _es8_total = es8_response['hits']['total']
            _total = (
                _es8_total['value']
                if _es8_total['relation'] == 'eq'
                else TROVE['ten-thousands-and-more']
            )
            _results = []
            for _es8_hit in es8_response['hits']['hits']:
                _card_iri = _es8_hit['_id']
                _results.append(CardsearchResult(
                    card_iri=_card_iri,
                    text_match_evidence=list(self._gather_textmatch_evidence(_es8_hit)),
                ))
            return CardsearchResponse(
                total_result_count=_total,
                search_result_page=_results,
                related_propertysearch_set=(),
            )

        def _gather_textmatch_evidence(self, es8_hit) -> Iterable[TextMatchEvidence]:
            for _innerhit_group in es8_hit.get('inner_hits', {}).values():
                for _innerhit in _innerhit_group['hits']['hits']:
                    _property_path = tuple(
                        json.loads(_innerhit['fields']['nested_text.path_from_focus'][0]),
                    )
                    try:
                        _language_iri = _innerhit['fields']['nested_text.language_iri'][0]
                    except KeyError:
                        _language_iri = None
                    for _highlight in _innerhit['highlight']['nested_text.text_value']:
                        yield TextMatchEvidence(
                            property_path=_property_path,
                            matching_highlight=primitive_rdf.text(_highlight, language_iri=_language_iri),
                            card_iri=_innerhit['_id'],
                        )

        class _TextQueryBuilder:
            def __init__(self, text_field, nested_path=None, inner_hits=None):
                self._text_field = text_field
                self._nested_path = nested_path
                self._inner_hits = inner_hits

            def _maybe_nested_query(self, query, *, with_inner_hits=False):
                if self._nested_path:
                    _nested_q = {'nested': {
                        'path': self._nested_path,
                        'query': query,
                    }}
                    if with_inner_hits and self._inner_hits:
                        _nested_q['nested']['inner_hits'] = self._inner_hits
                    return _nested_q
                return query

            def textsegment_queries(self, textsegment_set: Iterable[Textsegment], *, relevance_matters=True):
                _fuzzysegments = []
                for _textsegment in textsegment_set:
                    if _textsegment.is_negated:
                        yield 'must_not', self.excluded_text_query(_textsegment)
                    elif _textsegment.is_fuzzy:
                        _fuzzysegments.append(_textsegment)
                    else:
                        yield 'must', self.exact_text_query(_textsegment)
                if _fuzzysegments:
                    yield 'must', self.fuzzy_text_must_query(_fuzzysegments)
                    if relevance_matters:
                        for _should_query in self.fuzzy_text_should_queries(_fuzzysegments):
                            yield 'should', _should_query

            def excluded_text_query(self, textsegment: Textsegment) -> dict:
                return self._maybe_nested_query({'match_phrase': {
                    self._text_field: {
                        'query': textsegment.text,
                    },
                }})

            def exact_text_query(self, textsegment: Textsegment) -> dict:
                # TODO: textsegment.is_openended (prefix query)
                return self._maybe_nested_query({'match_phrase': {
                    self._text_field: {
                        'query': textsegment.text,
                    },
                }}, with_inner_hits=True)

            def fuzzy_text_must_query(self, textsegments: list[Textsegment]) -> dict:
                # TODO: textsegment.is_openended (prefix query)
                return self._maybe_nested_query({'match': {
                    self._text_field: {
                        'query': ' '.join(
                            _textsegment.text
                            for _textsegment in textsegments
                        ),
                        'fuzziness': 'AUTO',
                    },
                }}, with_inner_hits=True)

            def fuzzy_text_should_queries(self, textsegments: list[Textsegment]) -> Iterable[dict]:
                for _textsegment in textsegments:
                    yield self._maybe_nested_query({'match_phrase': {
                        self._text_field: {
                            'query': _textsegment.text,
                            'slop': len(_textsegment.words()),
                        },
                    }})


###
# module-local utils

def _bucketlist(agg_result: dict) -> list[str]:
    return [
        _bucket['key']
        for _bucket in agg_result['buckets']
    ]


class _PredicatePathWalker:
    @dataclasses.dataclass(frozen=True)
    class PathKey:
        path_from_start: tuple[str]
        nearest_subject_iri: str
        path_from_nearest_subject: tuple[str]

        def step(self, subject_or_blanknode, predicate_iri):
            if isinstance(subject_or_blanknode, str) and is_worthwhile_iri(subject_or_blanknode):
                return self.__class__(
                    path_from_start=(*self.path_from_start, predicate_iri),
                    nearest_subject_iri=subject_or_blanknode,
                    path_from_nearest_subject=(predicate_iri,),
                )
            return self.__class__(
                path_from_start=(*self.path_from_start, predicate_iri),
                nearest_subject_iri=self.nearest_subject_iri,
                path_from_nearest_subject=(*self.path_from_nearest_subject, predicate_iri),
            )

        @property
        def last_predicate_iri(self):
            return self.path_from_start[-1]

        def as_nested_keywords(self):
            return {
                'path_from_focus': iri_path_as_keyword(self.path_from_start),
                'property_iri': self.last_predicate_iri,
                'nearest_subject_iri': self.nearest_subject_iri,
                'nearest_subject_suffuniq_iri': get_sufficiently_unique_iri(self.nearest_subject_iri),
                'path_from_nearest_subject': iri_path_as_keyword(self.path_from_nearest_subject),
            }

    WalkYield = tuple[PathKey, primitive_rdf.RdfObject]

    def __init__(self, tripledict: primitive_rdf.RdfTripleDictionary):
        self.tripledict = tripledict
        self._visiting = set()

    def walk_from_subject(self, iri_or_blanknode, last_pathkey=None) -> Iterable[WalkYield]:
        '''walk the graph from the given subject, yielding (pathkey, obj) for every reachable object
        '''
        if last_pathkey is None:
            assert isinstance(iri_or_blanknode, str)
            last_pathkey = _PredicatePathWalker.PathKey(
                path_from_start=(),
                nearest_subject_iri=iri_or_blanknode,
                path_from_nearest_subject=(),
            )
        with self._visit(iri_or_blanknode):
            _twopledict = (
                primitive_rdf.twopleset_as_twopledict(iri_or_blanknode)
                if isinstance(iri_or_blanknode, frozenset)
                else self.tripledict.get(iri_or_blanknode, {})
            )
            for _predicate_iri, _obj_set in _twopledict.items():
                _pathkey = last_pathkey.step(iri_or_blanknode, _predicate_iri)
                for _obj in _obj_set:
                    if not isinstance(_obj, frozenset):  # omit the blanknode as a value
                        yield (_pathkey, _obj)
                    if isinstance(_obj, (str, frozenset)) and (_obj not in self._visiting):
                        # step further for iri or blanknode
                        yield from self.walk_from_subject(_obj, last_pathkey=_pathkey)

    @contextlib.contextmanager
    def _visit(self, focus_obj):
        assert focus_obj not in self._visiting
        self._visiting.add(focus_obj)
        yield
        self._visiting.discard(focus_obj)