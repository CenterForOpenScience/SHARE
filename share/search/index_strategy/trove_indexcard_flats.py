import base64
from collections import defaultdict
import contextlib
import dataclasses
import datetime
import json
import logging
import re
import uuid
from typing import Iterable, Optional

from django.conf import settings
from django.db.models import Exists, OuterRef
import elasticsearch8
from gather import primitive_rdf

from share.search import exceptions
from share.search import messages
from share.search.index_strategy.elastic8 import Elastic8IndexStrategy
from share.search.index_strategy._util import encode_cursor_dataclass, decode_cursor_dataclass
from share.search.search_params import (
    CardsearchParams,
    ValuesearchParams,
    SearchFilter,
    Textsegment,
    SortParam,
)
from share.search.search_response import (
    CardsearchResponse,
    ValuesearchResponse,
    TextMatchEvidence,
    CardsearchResult,
    ValuesearchResult,
    PropertypathUsage,
)
from share.util.checksum_iri import ChecksumIri
from trove import models as trove_db
from trove.util.iris import get_sufficiently_unique_iri, is_worthwhile_iri, iri_path_as_keyword
from trove.vocab.osfmap import is_date_property
from trove.vocab.namespaces import TROVE, FOAF, RDF, RDFS, DCTERMS, OWL, SKOS, OSFMAP


logger = logging.getLogger(__name__)


TITLE_PROPERTIES = (DCTERMS.title,)
NAME_PROPERTIES = (FOAF.name, OSFMAP.fileName)
LABEL_PROPERTIES = (RDFS.label, SKOS.prefLabel, SKOS.altLabel)
NAMELIKE_PROPERTIES = (*TITLE_PROPERTIES, *NAME_PROPERTIES, *LABEL_PROPERTIES)


SKIPPABLE_PROPERTIES = (
    OSFMAP.contains,
)


VALUESEARCH_MAX = 234
CARDSEARCH_MAX = 9997

KEYWORD_LENGTH_MAX = 8191  # skip keyword terms that might exceed lucene's internal limit
# (see https://www.elastic.co/guide/en/elasticsearch/reference/current/ignore-above.html)


class TroveIndexcardFlatsIndexStrategy(Elastic8IndexStrategy):
    CURRENT_STRATEGY_CHECKSUM = ChecksumIri(
        checksumalgorithm_name='sha-256',
        salt='TroveIndexcardFlatsIndexStrategy',
        hexdigest='bdec536873e1ed0c58facaa5d1145bef73bba09d671deef48e45c019def5c5a5',
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

    def index_settings(self):
        return {}

    def index_mappings(self):
        _capped_keyword = {
            'type': 'keyword',
            'ignore_above': KEYWORD_LENGTH_MAX,
        }
        _common_nested_keywords = {
            'path_from_focus': _capped_keyword,
            'suffuniq_path_from_focus': _capped_keyword,
            'property_iri': _capped_keyword,
            'distance_from_focus': {'type': 'keyword'},  # numeric value as keyword (used for 'term' filter)
        }
        return {
            'dynamic': 'false',
            'properties': {
                'indexcard_uuid': _capped_keyword,
                'focus_iri': _capped_keyword,
                'suffuniq_focus_iri': _capped_keyword,
                'source_record_identifier': _capped_keyword,
                'source_config_label': _capped_keyword,
                'flat_iri_values': {
                    'type': 'flattened',
                    'ignore_above': KEYWORD_LENGTH_MAX,
                },
                'flat_iri_values_suffuniq': {
                    'type': 'flattened',
                    'ignore_above': KEYWORD_LENGTH_MAX,
                },
                'iri_paths_present': _capped_keyword,
                'iri_paths_present_suffuniq': _capped_keyword,
                'nested_iri': {
                    'type': 'nested',
                    'properties': {
                        **_common_nested_keywords,
                        'iri_value': _capped_keyword,
                        'suffuniq_iri_value': _capped_keyword,
                        'value_type_iri': _capped_keyword,
                        'value_name_text': {
                            'type': 'text',
                            'fields': {'raw': _capped_keyword},
                            'copy_to': 'nested_iri.value_namelike_text',
                        },
                        'value_title_text': {
                            'type': 'text',
                            'fields': {'raw': _capped_keyword},
                            'copy_to': 'nested_iri.value_namelike_text',
                        },
                        'value_label_text': {
                            'type': 'text',
                            'fields': {'raw': _capped_keyword},
                            'copy_to': 'nested_iri.value_namelike_text',
                        },
                        'value_namelike_text': {'type': 'text'},
                    },
                },
                'nested_date': {
                    'type': 'nested',
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
        if _should_skip_card(indexcard_rdf, _rdfdoc):
            return None  # will be deleted from the index
        _nested_iris = defaultdict(set)
        _nested_dates = defaultdict(set)
        _nested_texts = defaultdict(set)
        _pathset = set()
        for _walk_path, _walk_obj in _PredicatePathWalker(_rdfdoc.tripledict).walk_from_subject(indexcard_rdf.focus_iri):
            _pathset.add(_walk_path)
            if isinstance(_walk_obj, str):
                _nested_iris[_NestedIriKey.for_iri_at_path(_walk_path, _walk_obj, _rdfdoc)].add(_walk_obj)
            elif isinstance(_walk_obj, datetime.date):
                _nested_dates[_walk_path].add(datetime.date.isoformat(_walk_obj))
            elif is_date_property(_walk_path[-1]):
                try:
                    datetime.date.fromisoformat(_walk_obj.unicode_text)
                except ValueError:
                    logger.debug('skipping malformatted date "%s" in %s', _walk_obj.unicode_text, indexcard_rdf)
                else:
                    _nested_dates[_walk_path].add(_walk_obj.unicode_text)
            elif isinstance(_walk_obj, primitive_rdf.Text):
                _nested_texts[(_walk_path, _walk_obj.language_iri)].add(_walk_obj.unicode_text)
        _focus_iris = {indexcard_rdf.focus_iri}
        _suffuniq_focus_iris = {get_sufficiently_unique_iri(indexcard_rdf.focus_iri)}
        for _identifier in indexcard_rdf.indexcard.focus_identifier_set.all():
            _focus_iris.update(_identifier.raw_iri_list)
            _suffuniq_focus_iris.add(_identifier.sufficiently_unique_iri)
        return {
            'indexcard_uuid': str(indexcard_rdf.indexcard.uuid),
            'focus_iri': list(_focus_iris),
            'suffuniq_focus_iri': list(_suffuniq_focus_iris),
            'source_record_identifier': indexcard_rdf.indexcard.source_record_suid.identifier,
            'source_config_label': indexcard_rdf.indexcard.source_record_suid.source_config.label,
            'flat_iri_values': self._flattened_iris(_nested_iris),
            'flat_iri_values_suffuniq': self._flattened_iris_suffuniq(_nested_iris),
            'iri_paths_present': [
                iri_path_as_keyword(_path)
                for _path in _pathset
            ],
            'iri_paths_present_suffuniq': [
                iri_path_as_keyword(_path, suffuniq=True)
                for _path in _pathset
            ],
            'nested_iri': list(filter(bool, (
                self._iri_nested_sourcedoc(_nested_iri_key, _iris, _rdfdoc)
                for _nested_iri_key, _iris in _nested_iris.items()
            ))),
            'nested_date': [
                {
                    **_iri_path_as_indexable_fields(_path),
                    'date_value': list(_value_set),
                }
                for _path, _value_set in _nested_dates.items()
            ],
            'nested_text': [
                {
                    **_iri_path_as_indexable_fields(_path),
                    'language_iri': _language_iri,
                    'text_value': list(_value_set),
                }
                for (_path, _language_iri), _value_set in _nested_texts.items()
            ],
        }

    def _iri_nested_sourcedoc(self, iri_key: '_NestedIriKey', iris, rdfdoc):
        _iris_with_synonyms = set(filter(is_worthwhile_iri, iris))
        for _iri in iris:
            _iris_with_synonyms.update(
                filter(is_worthwhile_iri, rdfdoc.q(_iri, OWL.sameAs)),
            )
        if not _iris_with_synonyms:
            return None
        _sourcedoc = {
            **iri_key.as_indexable_fields(),
            'iri_value': list(_iris_with_synonyms),
            'suffuniq_iri_value': [
                get_sufficiently_unique_iri(_iri)
                for _iri in _iris_with_synonyms
            ],
        }
        return _sourcedoc

    def _flattened_iris_by_path(self, nested_iris: dict['_NestedIriKey', set[str]]):
        _by_path = defaultdict(set)
        for _iri_key, _iris in nested_iris.items():
            _by_path[_iri_key.path].update(_iris)
        return _by_path

    def _flattened_iris(self, nested_iris: dict['_NestedIriKey', set[str]]):
        return {
            _iri_path_as_flattened_key(_path): list(_iris)
            for _path, _iris in self._flattened_iris_by_path(nested_iris).items()
        }

    def _flattened_iris_suffuniq(self, nested_iris: dict['_NestedIriKey', set[str]]):
        return {
            _iri_path_as_flattened_key(_path): [
                get_sufficiently_unique_iri(_iri)
                for _iri in _iris
            ]
            for _path, _iris in self._flattened_iris_by_path(nested_iris).items()
        }

    def build_elastic_actions(self, messages_chunk: messages.MessagesChunk):
        _indexcard_rdf_qs = (
            trove_db.LatestIndexcardRdf.objects
            .filter(indexcard_id__in=messages_chunk.target_ids_chunk)
            .filter(Exists(
                trove_db.DerivedIndexcard.objects
                .filter(upriver_indexcard_id=OuterRef('indexcard_id'))
                .filter(deriver_identifier__in=(
                    trove_db.ResourceIdentifier.objects
                    .queryset_for_iri(TROVE['derive/osfmap_json'])
                ))
            ))
            .exclude(indexcard__deleted__isnull=False)
            .select_related('indexcard__source_record_suid__source_config')
            .prefetch_related('indexcard__focus_identifier_set')
        )
        _remaining_indexcard_ids = set(messages_chunk.target_ids_chunk)
        for _indexcard_rdf in _indexcard_rdf_qs:
            _suid = _indexcard_rdf.indexcard.source_record_suid
            if _suid.has_forecompat_replacement():
                continue  # skip this one, let it get deleted
            _sourcedoc = self._build_sourcedoc(_indexcard_rdf)
            if _sourcedoc:
                _index_action = self.build_index_action(
                    doc_id=_indexcard_rdf.indexcard.get_iri(),
                    doc_source=_sourcedoc,
                )
                _remaining_indexcard_ids.discard(_indexcard_rdf.indexcard_id)
                yield _indexcard_rdf.indexcard_id, _index_action
        # delete any that don't have "latest" rdf and derived osfmap_json
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
            _cursor = _PageCursor.from_params(cardsearch_params)
            if cardsearch_params.sort_list:
                _sort = self._cardsearch_sort(cardsearch_params.sort_list)
                _relevance_matters = False
            else:
                _sort = None
                _relevance_matters = bool(cardsearch_params.cardsearch_textsegment_set)
            _query = self._cardsearch_query(
                cardsearch_params.cardsearch_filter_set,
                cardsearch_params.cardsearch_textsegment_set,
                relevance_matters=_relevance_matters,
                cursor=_cursor,
            )
            _search_kwargs = dict(
                query=_query,
                aggs=self._cardsearch_aggs(cardsearch_params),
                sort=_sort,
                from_=_cursor.query_start_index(),
                size=_cursor.page_size,
                source=False,  # no need to get _source; _id is enough
            )
            if settings.DEBUG:
                logger.info(json.dumps(_search_kwargs, indent=2))
            try:
                _es8_response = self.index_strategy.es8_client.search(
                    index=self.indexname,
                    **_search_kwargs,
                )
            except elasticsearch8.TransportError as error:
                raise exceptions.IndexStrategyError() from error  # TODO: error messaging
            return self._cardsearch_response(cardsearch_params, _es8_response, _cursor)

        def pls_handle_valuesearch(self, valuesearch_params: ValuesearchParams) -> ValuesearchResponse:
            _cursor = _PageCursor.from_params(valuesearch_params)
            _on_date_property = is_date_property(valuesearch_params.valuesearch_property_path[-1])
            try:
                _es8_response = self.index_strategy.es8_client.search(
                    index=self.indexname,
                    query=self._cardsearch_query(
                        valuesearch_params.cardsearch_filter_set,
                        valuesearch_params.cardsearch_textsegment_set,
                        relevance_matters=False,
                        additional_filters=[{'term': {
                            'iri_paths_present': iri_path_as_keyword(valuesearch_params.valuesearch_property_path),
                        }}],
                    ),
                    size=0,  # ignore cardsearch hits; just want the aggs
                    aggs=(
                        self._valuesearch_date_aggs(valuesearch_params, _cursor)
                        if _on_date_property
                        else self._valuesearch_iri_aggs(valuesearch_params, _cursor)
                    ),
                )
            except elasticsearch8.TransportError as error:
                raise exceptions.IndexStrategyError() from error  # TODO: error messaging
            return self._valuesearch_response(valuesearch_params, _es8_response, _cursor)

        ###
        # query implementation

        def _cardsearch_query(
            self,
            filter_set, textsegment_set, *,
            additional_filters=None,
            relevance_matters=True,
            cursor: Optional['_PageCursor'] = None,
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
                elif _searchfilter.operator == SearchFilter.FilterOperator.IS_PRESENT:
                    _bool_query['filter'].append(self._cardsearch_presence_query(_searchfilter))
                elif _searchfilter.operator == SearchFilter.FilterOperator.IS_ABSENT:
                    _bool_query['must_not'].append(self._cardsearch_presence_query(_searchfilter))
                elif _searchfilter.operator.is_date_operator():
                    _bool_query['filter'].append(self._cardsearch_date_filter(_searchfilter))
                else:
                    raise ValueError(f'unknown filter operator {_searchfilter.operator}')
            _textq_builder = self._TextQueryBuilder(
                'nested_text.text_value',
                nested_path='nested_text',
                nested_filter={'term': {'nested_text.distance_from_focus': 1}},
                inner_hits_factory=self._cardsearch_inner_hits,
            )
            for _boolkey, _textquery in _textq_builder.textsegment_queries(textsegment_set, relevance_matters=relevance_matters):
                _bool_query[_boolkey].append(_textquery)
            if not cursor or not cursor.random_sort:
                return {'bool': _bool_query}
            # how to sort by relevance to nothingness? randomness!
            if not cursor.first_page_uuids:
                # first page for the first time
                return {
                    'function_score': {
                        'query': {'bool': _bool_query},
                        'boost_mode': 'replace',
                        'random_score': {},  # default random_score is fast and unpredictable
                    },
                }
            _firstpage_uuid_query = {'terms': {'indexcard_uuid': cursor.first_page_uuids}}
            if cursor.is_first_page():
                # returning to a first page previously visited
                _bool_query['filter'].append(_firstpage_uuid_query)
                return {'bool': _bool_query}
            # get a subsequent page using reproducible randomness
            _bool_query['must_not'].append(_firstpage_uuid_query)
            return {
                'function_score': {
                    'query': {'bool': _bool_query},
                    'boost_mode': 'replace',
                    'random_score': {
                        'seed': ''.join(cursor.first_page_uuids),
                        'field': 'indexcard_uuid',
                    },
                },
            }

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

        def _cardsearch_aggs(self, cardsearch_params):
            _aggs = {}
            if cardsearch_params.related_property_paths:
                _aggs['related_propertypath_usage'] = {'terms': {
                    'field': 'iri_paths_present',
                    'include': [
                        iri_path_as_keyword(_path)
                        for _path in cardsearch_params.related_property_paths
                    ],
                    'size': len(cardsearch_params.related_property_paths),
                }}
            if cardsearch_params.unnamed_iri_values:
                _aggs['global_agg'] = {
                    'global': {},
                    'aggs': {
                        'filtervalue_info': {
                            'nested': {'path': 'nested_iri'},
                            'aggs': {
                                'iri_values': {
                                    'terms': {
                                        'field': 'nested_iri.iri_value',
                                        'include': list(cardsearch_params.unnamed_iri_values),
                                        'size': len(cardsearch_params.unnamed_iri_values),
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
                }
            return _aggs

        def _valuesearch_iri_aggs(self, valuesearch_params: ValuesearchParams, cursor: '_PageCursor'):
            # TODO: valuesearch_filter_set (just rdf:type => nested_iri.value_type_iri)
            _nested_iri_bool = {
                'filter': [{'term': {'nested_iri.suffuniq_path_from_focus': iri_path_as_keyword(
                    valuesearch_params.valuesearch_property_path,
                    suffuniq=True,
                )}}],
                'must': [],
                'must_not': [],
                'should': [],
            }
            _textq_builder = self._TextQueryBuilder('nested_iri.value_namelike_text')
            for _boolkey, _textquery in _textq_builder.textsegment_queries(valuesearch_params.valuesearch_textsegment_set):
                _nested_iri_bool[_boolkey].append(_textquery)
            return {
                'in_nested_iri': {
                    'nested': {'path': 'nested_iri'},
                    'aggs': {
                        'value_at_propertypath': {
                            'filter': {'bool': _nested_iri_bool},
                            'aggs': {
                                'iri_value_cardinality': {
                                    'cardinality': {
                                        'field': 'nested_iri.iri_value',
                                    },
                                },
                                'iri_values': {
                                    'terms': {
                                        'field': 'nested_iri.iri_value',
                                        # WARNING: terribly inefficient pagination (part one)
                                        'size': cursor.start_index + cursor.page_size + 1,
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

        def _valuesearch_date_aggs(self, valuesearch_params: ValuesearchParams, cursor: '_PageCursor'):
            _aggs = {
                'in_nested_date': {
                    'nested': {'path': 'nested_date'},
                    'aggs': {
                        'value_at_propertypath': {
                            'filter': {'term': {
                                'nested_date.suffuniq_path_from_focus': iri_path_as_keyword(
                                    valuesearch_params.valuesearch_property_path,
                                    suffuniq=True,
                                ),
                            }},
                            'aggs': {
                                'count_by_year': {
                                    'date_histogram': {
                                        'field': 'nested_date.date_value',
                                        'calendar_interval': 'year',
                                        'format': 'yyyy',
                                        'order': {'_key': 'desc'},
                                        'min_doc_count': 1,
                                    },
                                },
                            },
                        },
                    },
                },
            }
            return _aggs

        def _valuesearch_response(
            self,
            valuesearch_params: ValuesearchParams,
            es8_response: dict,
            cursor: '_PageCursor',
        ):
            _iri_aggs = es8_response['aggregations'].get('in_nested_iri')
            if _iri_aggs:
                _buckets = _iri_aggs['value_at_propertypath']['iri_values']['buckets']
                # WARNING: terribly inefficient pagination (part two)
                _page_end_index = cursor.start_index + cursor.page_size
                _bucket_page = _buckets[cursor.start_index:_page_end_index]
                _more_pages = (len(_buckets) > _page_end_index)  # agg includes one more, if there
                return ValuesearchResponse(
                    total_result_count=_iri_aggs['value_at_propertypath']['iri_value_cardinality']['value'],
                    search_result_page=[
                        self._valuesearch_iri_result(_iri_bucket)
                        for _iri_bucket in _bucket_page[:cursor.page_size]
                    ],
                    next_page_cursor=(
                        cursor.next_cursor(VALUESEARCH_MAX)
                        if _more_pages
                        else None
                    ),
                    prev_page_cursor=cursor.prev_cursor(),
                    first_page_cursor=cursor.first_cursor(),
                )
            else:  # assume date
                _year_buckets = (
                    es8_response['aggregations']['in_nested_date']
                    ['value_at_propertypath']['count_by_year']['buckets']
                )
                return ValuesearchResponse(
                    search_result_page=[
                        self._valuesearch_date_result(_year_bucket)
                        for _year_bucket in _year_buckets
                    ],
                )

        def _valuesearch_iri_result(self, iri_bucket):
            return ValuesearchResult(
                value_iri=iri_bucket['key'],
                value_type=_bucketlist(iri_bucket['type_iri']),
                name_text=_bucketlist(iri_bucket['name_text']),
                title_text=_bucketlist(iri_bucket['title_text']),
                label_text=_bucketlist(iri_bucket['label_text']),
                match_count=iri_bucket['doc_count'],
            )

        def _valuesearch_date_result(self, date_bucket):
            return ValuesearchResult(
                value_iri=None,
                value_value=date_bucket['key_as_string'],
                label_text=(date_bucket['key_as_string'],),
                match_count=date_bucket['doc_count'],
            )

        def _cardsearch_presence_query(self, search_filter) -> dict:
            _path_keyword = iri_path_as_keyword(search_filter.property_path, suffuniq=True)
            return {'term': {'iri_paths_present_suffuniq': _path_keyword}}

        def _cardsearch_iri_filter(self, search_filter) -> dict:
            _field = '.'.join((
                'flat_iri_values_suffuniq',
                _iri_path_as_flattened_key(search_filter.property_path),
            ))
            return {'terms': {
                _field: [
                    get_sufficiently_unique_iri(_iri)
                    for _iri in search_filter.value_set
                ],
            }}

        def _cardsearch_date_filter(self, search_filter) -> dict:
            _propertypath_keyword = iri_path_as_keyword(search_filter.property_path, suffuniq=True)
            _filter_list = [
                {'term': {'nested_date.suffuniq_path_from_focus': _propertypath_keyword}},
            ]
            if search_filter.operator == SearchFilter.FilterOperator.BEFORE:
                _value = min(search_filter.value_set)  # rely on string-comparable isoformat
                _filter_list.append({'range': {'nested_date.date_value': {
                    'lt': _daterange_value_and_format(_value)
                }}})
            elif search_filter.operator == SearchFilter.FilterOperator.AFTER:
                _value = max(search_filter.value_set)  # rely on string-comparable isoformat
                _filter_list.append({'range': {'nested_date.date_value': {
                    'gt': _daterange_value_and_format(_value)
                }}})
            elif search_filter.operator == SearchFilter.FilterOperator.AT_DATE:
                for _value in search_filter.value_set:
                    _filtervalue = _daterange_value_and_format(_value)
                    _filter_list.append({'range': {'nested_date.date_value': {
                        'gte': _filtervalue,
                        'lte': _filtervalue,
                    }}})
            else:
                raise ValueError(f'invalid date filter operator (got {search_filter.operator})')
            return {'nested': {
                'path': 'nested_date',
                'query': {'bool': {'filter': _filter_list}},
            }}

        def _cardsearch_sort(self, sort_list: tuple[SortParam]):
            return [
                {'nested_date.date_value': {
                    'order': ('desc' if _sortparam.descending else 'asc'),
                    'nested': {
                        'path': 'nested_date',
                        'filter': {'term': {
                            'nested_date.suffuniq_path_from_focus': iri_path_as_keyword(
                                [_sortparam.property_iri],
                                suffuniq=True,
                            ),
                        }},
                    },
                }}
                for _sortparam in sort_list
            ]

        def _cardsearch_response(
            self,
            cardsearch_params: CardsearchParams,
            es8_response: dict,
            cursor: '_PageCursor',
        ) -> CardsearchResponse:
            _pagination_disabled = (
                cursor.random_sort
                and not any(
                    _filter.property_path != (RDF.type,)
                    for _filter in cardsearch_params.cardsearch_filter_set
                )
            )
            _es8_total = es8_response['hits']['total']
            if _pagination_disabled or _es8_total['relation'] != 'eq':
                _total = TROVE['ten-thousands-and-more']  # if pagination disabled, this may be an exaggeration
            else:
                _total = _es8_total['value']
                if cursor.random_sort and not cursor.is_first_page():
                    _total += len(cursor.first_page_uuids)
            if _pagination_disabled:
                _cursor_kwargs = {
                    'next_page_cursor': None,
                    'prev_page_cursor': None,
                    'first_page_cursor': None,
                }
            else:
                if cursor.random_sort and cursor.is_first_page() and not cursor.first_page_uuids:
                    cursor.first_page_uuids = tuple(
                        _hit['_id'].rpartition('/')[-1]
                        for _hit in es8_response['hits']['hits']
                    )
                _cursor_kwargs = {
                    'next_page_cursor': cursor.next_cursor(
                        _total
                        if isinstance(_total, int)
                        else CARDSEARCH_MAX
                    ),
                    'prev_page_cursor': cursor.prev_cursor(),
                    'first_page_cursor': cursor.first_cursor(),
                }
            _results = []
            for _es8_hit in es8_response['hits']['hits']:
                _card_iri = _es8_hit['_id']
                _results.append(CardsearchResult(
                    card_iri=_card_iri,
                    text_match_evidence=list(self._gather_textmatch_evidence(_es8_hit)),
                ))
            _filtervalue_info = []
            if cardsearch_params.unnamed_iri_values:
                _filtervalue_agg = es8_response['aggregations']['global_agg']['filtervalue_info']['iri_values']
                _filtervalue_info.extend(
                    self._valuesearch_iri_result(_iri_bucket)
                    for _iri_bucket in _filtervalue_agg['buckets']
                )
            _relatedproperty_list = []
            if cardsearch_params.related_property_paths:
                _relatedproperty_list.extend(
                    PropertypathUsage(property_path=_path, usage_count=0)
                    for _path in cardsearch_params.related_property_paths
                )
                _relatedproperty_by_path = {
                    _result.property_path: _result
                    for _result in _relatedproperty_list
                }
                for _bucket in es8_response['aggregations']['related_propertypath_usage']['buckets']:
                    _path = tuple(json.loads(_bucket['key']))
                    _relatedproperty_by_path[_path].usage_count += _bucket['doc_count']
            return CardsearchResponse(
                total_result_count=_total,
                search_result_page=_results,
                filtervalue_info=_filtervalue_info,
                related_propertypath_results=_relatedproperty_list,
                **_cursor_kwargs,
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

        class _TextQueryBuilder:  # TODO: when adding field-specific text queries, move "nested" logic to subclass
            def __init__(self, text_field, *, nested_path=None, nested_filter=None, inner_hits_factory=None):
                self._text_field = text_field
                self._nested_path = nested_path
                self._nested_filter = nested_filter
                self._inner_hits_factory = inner_hits_factory

            def _maybe_nested_query(self, query, *, with_inner_hits=False):
                if self._nested_path:
                    _inner_query = (
                        {'bool': {
                            'filter': self._nested_filter,
                            'must': query,
                        }}
                        if self._nested_filter
                        else query
                    )
                    _nested_q = {'nested': {
                        'path': self._nested_path,
                        'query': _inner_query,
                    }}
                    if with_inner_hits and self._inner_hits_factory:
                        _nested_q['nested']['inner_hits'] = self._inner_hits_factory()
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

def _should_skip_card(indexcard_rdf, rdfdoc):
    # skip cards without some value for name/title/label
    return not any(rdfdoc.q(indexcard_rdf.focus_iri, NAMELIKE_PROPERTIES))


def _bucketlist(agg_result: dict) -> list[str]:
    return [
        _bucket['key']
        for _bucket in agg_result['buckets']
    ]


def _daterange_value_and_format(datevalue: str):
    _cleanvalue = datevalue.strip()
    if re.fullmatch(r'\d{4,}', _cleanvalue):
        return f'{_cleanvalue}||/y'
    if re.fullmatch(r'\d{4,}-\d{2}', _cleanvalue):
        return f'{_cleanvalue}||/M'
    if re.fullmatch(r'\d{4,}-\d{2}-\d{2}', _cleanvalue):
        return f'{_cleanvalue}||/d'
    raise ValueError(f'bad date value "{datevalue}"')


def _iri_path_as_indexable_fields(path: tuple[str, ...]):
    assert path, 'path should not be empty'
    return {
        'path_from_focus': iri_path_as_keyword(path),
        'suffuniq_path_from_focus': iri_path_as_keyword(path, suffuniq=True),
        'property_iri': path[-1],
        'distance_from_focus': len(path),
    }


def _iri_path_as_flattened_key(path: tuple[str, ...]) -> str:
    return base64.b16encode(json.dumps(path).encode()).decode()


@dataclasses.dataclass
class _PageCursor:
    start_index: int
    page_size: int
    random_sort: bool
    first_page_uuids: tuple[str, ...]

    @classmethod
    def from_params(cls, params: CardsearchParams) -> '_PageCursor':
        if params.page.cursor:
            return decode_cursor_dataclass(params.page.cursor, cls)
        return cls(
            start_index=0,
            page_size=params.page.size,
            random_sort=not (params.sort_list or params.cardsearch_textsegment_set),
            first_page_uuids=(),
        )

    def next_cursor(self, maximum_index: int) -> str | None:
        _next = dataclasses.replace(self, start_index=(self.start_index + self.page_size))
        return (
            encode_cursor_dataclass(_next)
            if _next.start_index < maximum_index
            else None
        )

    def prev_cursor(self) -> str | None:
        _prev = dataclasses.replace(self, start_index=(self.start_index - self.page_size))
        return (
            encode_cursor_dataclass(_prev)
            if _prev.start_index >= 0
            else None
        )

    def first_cursor(self) -> str | None:
        if self.is_first_page():
            return None
        return encode_cursor_dataclass(dataclasses.replace(self, start_index=0))

    def is_first_page(self) -> bool:
        return self.start_index == 0

    def query_start_index(self) -> int:
        if self.is_first_page() or not self.random_sort:
            return self.start_index
        return self.start_index - len(self.first_page_uuids)


class _PredicatePathWalker:
    WalkYield = tuple[tuple[str, ...], primitive_rdf.RdfObject]

    def __init__(self, tripledict: primitive_rdf.RdfTripleDictionary):
        self.tripledict = tripledict
        self._visiting = set()

    def walk_from_subject(self, iri_or_blanknode, last_path: tuple[str, ...] = ()) -> Iterable[WalkYield]:
        '''walk the graph from the given subject, yielding (pathkey, obj) for every reachable object
        '''
        with self._visit(iri_or_blanknode):
            _twopledict = (
                primitive_rdf.twopleset_as_twopledict(iri_or_blanknode)
                if isinstance(iri_or_blanknode, frozenset)
                else self.tripledict.get(iri_or_blanknode, {})
            )
            for _predicate_iri, _obj_set in _twopledict.items():
                if _predicate_iri not in SKIPPABLE_PROPERTIES:
                    _path = (*last_path, _predicate_iri)
                    for _obj in _obj_set:
                        if not isinstance(_obj, frozenset):  # omit the blanknode as a value
                            yield (_path, _obj)
                        if isinstance(_obj, (str, frozenset)) and (_obj not in self._visiting):
                            # step further for iri or blanknode
                            yield from self.walk_from_subject(_obj, last_path=_path)

    @contextlib.contextmanager
    def _visit(self, focus_obj):
        assert focus_obj not in self._visiting
        self._visiting.add(focus_obj)
        yield
        self._visiting.discard(focus_obj)


@dataclasses.dataclass(frozen=True)
class _NestedIriKey:
    '''if this is the same for multiple iri values, they can be combined in one `nested_iri` doc
    '''
    path: tuple[str, ...]
    type_iris: frozenset[str]
    label_text: frozenset[str]
    title_text: frozenset[str]
    name_text: frozenset[str]

    @classmethod
    def for_iri_at_path(cls, path: tuple[str, ...], iri: str, rdfdoc):
        return cls(
            path=path,
            type_iris=frozenset(rdfdoc.q(iri, RDF.type)),
            # TODO: don't discard language for name/title/label
            name_text=frozenset(
                _text.unicode_text
                for _text in rdfdoc.q(iri, NAME_PROPERTIES)
                if isinstance(_text, primitive_rdf.Text)
            ),
            title_text=frozenset(
                _text.unicode_text
                for _text in rdfdoc.q(iri, TITLE_PROPERTIES)
                if isinstance(_text, primitive_rdf.Text)
            ),
            label_text=frozenset(
                _text.unicode_text
                for _text in rdfdoc.q(iri, LABEL_PROPERTIES)
                if isinstance(_text, primitive_rdf.Text)
            ),
        )

    def as_indexable_fields(self):
        # matches fields in the mapping for `nested_iri`, above
        return {
            **_iri_path_as_indexable_fields(self.path),
            'value_type_iri': list(self.type_iris),
            'value_label_text': list(self.label_text),
            'value_title_text': list(self.title_text),
            'value_name_text': list(self.name_text),
        }
