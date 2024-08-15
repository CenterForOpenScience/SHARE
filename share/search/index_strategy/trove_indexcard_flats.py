import base64
from collections import defaultdict
import contextlib
import dataclasses
import datetime
import json
import logging
import re
import uuid
from typing import Iterable, ClassVar, Optional, Iterator

from django.conf import settings
from django.db.models import Exists, OuterRef
import elasticsearch8
from primitive_metadata import primitive_rdf

from share.search import exceptions
from share.search import messages
from share.search.index_strategy.elastic8 import Elastic8IndexStrategy
from share.search.index_strategy._util import encode_cursor_dataclass, decode_cursor_dataclass
from share.util.checksum_iri import ChecksumIri
from trove import models as trove_db
from trove.trovesearch.search_params import (
    CardsearchParams,
    ValuesearchParams,
    SearchFilter,
    Textsegment,
    SortParam,
    PageParam,
    GLOB_PATHSTEP,
)
from trove.trovesearch.search_response import (
    CardsearchResponse,
    ValuesearchResponse,
    TextMatchEvidence,
    CardsearchResult,
    ValuesearchResult,
    PropertypathUsage,
)
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
        _rdfdoc = primitive_rdf.RdfGraph(indexcard_rdf.as_rdf_tripledict())
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
                    datetime.date.fromisoformat(_walk_obj.unicode_value)
                except ValueError:
                    logger.debug('skipping malformatted date "%s" in %s', _walk_obj.unicode_value, indexcard_rdf)
                else:
                    _nested_dates[_walk_path].add(_walk_obj.unicode_value)
            elif isinstance(_walk_obj, primitive_rdf.Literal):
                _nested_texts[(_walk_path, tuple(_walk_obj.datatype_iris))].add(_walk_obj.unicode_value)
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
                    'language_iri': _language_iris,
                    'text_value': list(_value_set),
                }
                for (_path, _language_iris), _value_set in _nested_texts.items()
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
            _cursor = _CardsearchCursor.from_params(cardsearch_params)
            _sort = self._cardsearch_sort(cardsearch_params.sort_list)
            _query = self._cardsearch_query(
                cardsearch_params.cardsearch_filter_set,
                cardsearch_params.cardsearch_textsegment_set,
                cardsearch_cursor=_cursor,
            )
            _search_kwargs = dict(
                query=_query,
                aggs=self._cardsearch_aggs(cardsearch_params),
                sort=_sort,
                from_=_cursor.cardsearch_start_index(),
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
            _cursor = _SimpleCursor.from_page_param(valuesearch_params.page)
            _is_date_search = is_date_property(valuesearch_params.valuesearch_propertypath[-1])
            _search_kwargs = dict(
                query=self._cardsearch_query(
                    valuesearch_params.cardsearch_filter_set,
                    valuesearch_params.cardsearch_textsegment_set,
                    additional_filters=[{'term': {'iri_paths_present': iri_path_as_keyword(
                        valuesearch_params.valuesearch_propertypath,
                    )}}],
                ),
                size=0,  # ignore cardsearch hits; just want the aggs
                aggs=(
                    self._valuesearch_date_aggs(valuesearch_params)
                    if _is_date_search
                    else self._valuesearch_iri_aggs(valuesearch_params, _cursor)
                ),
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
            return self._valuesearch_response(valuesearch_params, _es8_response, _cursor)

        ###
        # query implementation

        def _cardsearch_query(
            self,
            filter_set, textsegment_set, *,
            additional_filters=None,
            cardsearch_cursor: Optional['_CardsearchCursor'] = None,
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
            _textq_builder = self._NestedTextQueryBuilder(
                relevance_matters=bool(cardsearch_cursor and not cardsearch_cursor.random_sort),
            )
            for _textsegment in textsegment_set:
                for _boolkey, _textqueries in _textq_builder.textsegment_boolparts(_textsegment).items():
                    _bool_query[_boolkey].extend(_textqueries)
            if not cardsearch_cursor or not cardsearch_cursor.random_sort:
                # no need for randomness
                return {'bool': _bool_query}
            if not cardsearch_cursor.first_page_uuids:
                # independent random sample
                return {
                    'function_score': {
                        'query': {'bool': _bool_query},
                        'boost_mode': 'replace',
                        'random_score': {},  # default random_score is fast and unpredictable
                    },
                }
            _firstpage_uuid_query = {'terms': {'indexcard_uuid': cardsearch_cursor.first_page_uuids}}
            if cardsearch_cursor.is_first_page():
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
                        'seed': ''.join(cardsearch_cursor.first_page_uuids),
                        'field': 'indexcard_uuid',
                    },
                },
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
            return _aggs

        def _valuesearch_iri_aggs(self, valuesearch_params: ValuesearchParams, cursor: '_SimpleCursor'):
            _nested_iri_bool = {
                'filter': [{'term': {'nested_iri.suffuniq_path_from_focus': iri_path_as_keyword(
                    valuesearch_params.valuesearch_propertypath,
                    suffuniq=True,
                )}}],
                'must': [],
                'must_not': [],
                'should': [],
            }
            _nested_terms_agg = {
                'field': 'nested_iri.iri_value',
                # WARNING: terribly inefficient pagination (part one)
                'size': cursor.start_index + cursor.page_size + 1,
            }
            _iris = list(valuesearch_params.valuesearch_iris())
            if _iris:
                _nested_iri_bool['filter'].append({'terms': {
                    'nested_iri.iri_value': _iris,
                }})
                _nested_terms_agg['size'] = len(_iris)
                _nested_terms_agg['include'] = _iris
            _type_iris = list(valuesearch_params.valuesearch_type_iris())
            if _type_iris:
                _nested_iri_bool['filter'].append({'terms': {
                    'nested_iri.value_type_iri': _type_iris,
                }})
            _textq_builder = self._SimpleTextQueryBuilder('nested_iri.value_namelike_text')
            for _textsegment in valuesearch_params.valuesearch_textsegment_set:
                for _boolkey, _textqueries in _textq_builder.textsegment_boolparts(_textsegment).items():
                    _nested_iri_bool[_boolkey].extend(_textqueries)
            return {
                'in_nested_iri': {
                    'nested': {'path': 'nested_iri'},
                    'aggs': {
                        'value_at_propertypath': {
                            'filter': {'bool': _nested_iri_bool},
                            'aggs': {
                                'iri_values': {
                                    'terms': _nested_terms_agg,
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

        def _valuesearch_date_aggs(self, valuesearch_params: ValuesearchParams):
            _aggs = {
                'in_nested_date': {
                    'nested': {'path': 'nested_date'},
                    'aggs': {
                        'value_at_propertypath': {
                            'filter': {'term': {
                                'nested_date.suffuniq_path_from_focus': iri_path_as_keyword(
                                    valuesearch_params.valuesearch_propertypath,
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
            cursor: '_SimpleCursor',
        ):
            _iri_aggs = es8_response['aggregations'].get('in_nested_iri')
            if _iri_aggs:
                _buckets = _iri_aggs['value_at_propertypath']['iri_values']['buckets']
                _bucket_count = len(_buckets)
                # WARNING: terribly inefficient pagination (part two)
                _page_end_index = cursor.start_index + cursor.page_size
                _bucket_page = _buckets[cursor.start_index:_page_end_index]  # discard prior pages
                cursor.result_count = (
                    -1  # "many more"
                    if (_bucket_count > _page_end_index)  # agg includes one more, if there
                    else _bucket_count
                )
                return ValuesearchResponse(
                    search_result_page=[
                        self._valuesearch_iri_result(_iri_bucket)
                        for _iri_bucket in _bucket_page
                    ],
                    next_page_cursor=cursor.next_cursor(),
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
            _filters = [
                self._cardsearch_path_presence_query(_path)
                for _path in search_filter.propertypath_set
            ]
            if len(_filters) == 1:
                return _filters[0]
            return {'bool': {
                'minimum_should_match': 1,
                'should': _filters,
            }}

        def _cardsearch_path_presence_query(self, path: tuple[str, ...]):
            if all(_pathstep == GLOB_PATHSTEP for _pathstep in path):
                return {'nested': {
                    'path': 'nested_iri',
                    'query': {'term': {'nested_iri.distance_from_focus': len(path)}},
                }}
            return {'term': {
                'iri_paths_present_suffuniq': iri_path_as_keyword(path, suffuniq=True),
            }}

        def _cardsearch_iri_filter(self, search_filter) -> dict:
            _filters = [
                self._cardsearch_path_iri_query(_path, search_filter.value_set)
                for _path in search_filter.propertypath_set
            ]
            if len(_filters) == 1:
                return _filters[0]
            return {'bool': {
                'minimum_should_match': 1,
                'should': _filters,
            }}

        def _cardsearch_path_iri_query(self, path, value_set):
            _suffuniq_values = [
                get_sufficiently_unique_iri(_iri)
                for _iri in value_set
            ]
            if all(_pathstep == GLOB_PATHSTEP for _pathstep in path):
                return {'nested': {
                    'path': 'nested_iri',
                    'query': {'bool': {
                        'must': [  # both
                            {'term': {'nested_iri.distance_from_focus': len(path)}},
                            {'terms': {'nested_iri.suffuniq_iri_value': _suffuniq_values}},
                        ],
                    }},
                }}
            # without a glob-path, can use the flattened keyword field
            return {'terms': {_iri_path_as_flattened_field(path): _suffuniq_values}}

        def _cardsearch_date_filter(self, search_filter):
            return {'nested': {
                'path': 'nested_date',
                'query': {'bool': {'filter': list(self._iter_nested_date_filters(search_filter))}},
            }}

        def _iter_nested_date_filters(self, search_filter) -> Iterator[dict]:
            # filter by requested paths
            yield _pathset_as_nestedvalue_filter(search_filter.propertypath_set, 'nested_date')
            # filter by requested value/operator
            if search_filter.operator == SearchFilter.FilterOperator.BEFORE:
                _value = min(search_filter.value_set)  # rely on string-comparable isoformat
                yield {'range': {'nested_date.date_value': {
                    'lt': _daterange_value_and_format(_value)
                }}}
            elif search_filter.operator == SearchFilter.FilterOperator.AFTER:
                _value = max(search_filter.value_set)  # rely on string-comparable isoformat
                yield {'range': {'nested_date.date_value': {
                    'gt': _daterange_value_and_format(_value)
                }}}
            elif search_filter.operator == SearchFilter.FilterOperator.AT_DATE:
                for _value in search_filter.value_set:
                    _filtervalue = _daterange_value_and_format(_value)
                    yield {'range': {'nested_date.date_value': {
                        'gte': _filtervalue,
                        'lte': _filtervalue,
                    }}}
            else:
                raise ValueError(f'invalid date filter operator (got {search_filter.operator})')

        def _cardsearch_sort(self, sort_list: tuple[SortParam]):
            if not sort_list:
                return None
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
            cursor: '_CardsearchCursor',
        ) -> CardsearchResponse:
            _es8_total = es8_response['hits']['total']
            if _es8_total['relation'] != 'eq':
                cursor.result_count = -1  # "too many"
            else:  # exact (and small) count
                cursor.result_count = _es8_total['value']
                if cursor.random_sort and not cursor.is_first_page():
                    # account for the filtered-out first page
                    cursor.result_count += len(cursor.first_page_uuids)
            _results = []
            for _es8_hit in es8_response['hits']['hits']:
                _card_iri = _es8_hit['_id']
                _results.append(CardsearchResult(
                    card_iri=_card_iri,
                    text_match_evidence=list(self._gather_textmatch_evidence(_es8_hit)),
                ))
            if cursor.is_first_page() and cursor.first_page_uuids:
                # revisiting first page; reproduce original random order
                _uuid_index = {
                    _uuid: _i
                    for (_i, _uuid) in enumerate(cursor.first_page_uuids)
                }
                _results.sort(key=lambda _r: _uuid_index[_r.card_uuid])
            else:
                _should_start_reproducible_randomness = (
                    cursor.random_sort
                    and cursor.is_first_page()
                    and not cursor.first_page_uuids
                    and any(
                        not _filter.is_type_filter()  # look for a non-default filter
                        for _filter in cardsearch_params.cardsearch_filter_set
                    )
                )
                if _should_start_reproducible_randomness:
                    cursor.first_page_uuids = tuple(
                        _result.card_uuid
                        for _result in _results
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
                total_result_count=(
                    TROVE['ten-thousands-and-more']
                    if cursor.has_many_more()
                    else cursor.result_count
                ),
                search_result_page=_results,
                related_propertypath_results=_relatedproperty_list,
                next_page_cursor=cursor.next_cursor(),
                prev_page_cursor=cursor.prev_cursor(),
                first_page_cursor=cursor.first_cursor(),
            )

        def _gather_textmatch_evidence(self, es8_hit) -> Iterable[TextMatchEvidence]:
            for _innerhit_group in es8_hit.get('inner_hits', {}).values():
                for _innerhit in _innerhit_group['hits']['hits']:
                    _property_path = tuple(
                        json.loads(_innerhit['fields']['nested_text.path_from_focus'][0]),
                    )
                    try:
                        _language_iris = _innerhit['fields']['nested_text.language_iri']
                    except KeyError:
                        _language_iris = ()
                    for _highlight in _innerhit['highlight']['nested_text.text_value']:
                        yield TextMatchEvidence(
                            property_path=_property_path,
                            matching_highlight=primitive_rdf.literal(_highlight, datatype_iris=_language_iris),
                            card_iri=_innerhit['_id'],
                        )

        class _SimpleTextQueryBuilder:
            def __init__(
                self, text_field, *,
                relevance_matters=False,
            ):
                self._text_field = text_field
                self._relevance_matters = relevance_matters

            def textsegment_boolparts(self, textsegment: Textsegment) -> dict[str, list]:
                if textsegment.is_negated:
                    return {'must_not': [self.exact_text_query(textsegment.text)]}
                if not textsegment.is_fuzzy:
                    return {'must': [self.exact_text_query(textsegment.text)]}
                if not self._relevance_matters:
                    return {'must': [self.fuzzy_text_must_query(textsegment.text)]}
                return {
                    'must': [self.fuzzy_text_must_query(textsegment.text)],
                    'should': [self.fuzzy_text_should_query(textsegment.text)],
                }

            def exact_text_query(self, text: str) -> dict:
                # TODO: textsegment.is_openended (prefix query)
                return {'match_phrase': {
                    self._text_field: {'query': text},
                }}

            def fuzzy_text_must_query(self, text: str) -> dict:
                # TODO: textsegment.is_openended (prefix query)
                return {'match': {
                    self._text_field: {
                        'query': text,
                        'fuzziness': 'AUTO',
                        # TODO: 'operator': 'and' (by query param FilterOperator, `cardSearchText[*][every-word]=...`)
                    },
                }}

            def fuzzy_text_should_query(self, text: str):
                return {'match_phrase': {
                    self._text_field: {
                        'query': text,
                        'slop': len(text.split()),
                    },
                }}

        class _NestedTextQueryBuilder(_SimpleTextQueryBuilder):
            def __init__(self, **kwargs):
                super().__init__('nested_text.text_value', **kwargs)

            def textsegment_boolparts(self, textsegment: Textsegment) -> dict[str, list]:
                return {
                    _boolkey: [
                        self._make_nested_query(textsegment, _query)
                        for _query in _queries
                    ]
                    for _boolkey, _queries in super().textsegment_boolparts(textsegment).items()
                }

            def _make_nested_query(self, textsegment, query):
                _nested_q = {'nested': {
                    'path': 'nested_text',
                    'query': {'bool': {
                        'filter': _pathset_as_nestedvalue_filter(textsegment.propertypath_set, 'nested_text'),
                        'must': query,
                    }},
                }}
                if self._relevance_matters:
                    _nested_q['nested']['inner_hits'] = self._inner_hits()
                return _nested_q

            def _inner_hits(self, *, highlight_query=None) -> dict:
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


def _iri_path_as_flattened_field(path: tuple[str, ...]) -> str:
    return f'flat_iri_values_suffuniq.{_iri_path_as_flattened_key(path)}'


def _pathset_as_nestedvalue_filter(propertypath_set: frozenset[tuple[str, ...]], nested_path: str):
    _suffuniq_iri_paths = []
    _glob_path_lengths = []
    for _path in propertypath_set:
        if all(_pathstep == GLOB_PATHSTEP for _pathstep in _path):
            _glob_path_lengths.append(len(_path))
        else:
            _suffuniq_iri_paths.append(iri_path_as_keyword(_path, suffuniq=True))
    if _suffuniq_iri_paths and _glob_path_lengths:
        return {'bool': {
            'minimum_should_match': 1,
            'should': [
                {'terms': {f'{nested_path}.distance_from_focus': _glob_path_lengths}},
                {'terms': {f'{nested_path}.suffuniq_path_from_focus': _suffuniq_iri_paths}},
            ],
        }}
    if _glob_path_lengths:
        return {'terms': {f'{nested_path}.distance_from_focus': _glob_path_lengths}}
    return {'terms': {f'{nested_path}.suffuniq_path_from_focus': _suffuniq_iri_paths}}


@dataclasses.dataclass
class _SimpleCursor:
    start_index: int
    page_size: int
    result_count: int | None  # use -1 to indicate "many more"

    MAX_INDEX: ClassVar[int] = VALUESEARCH_MAX

    @classmethod
    def from_page_param(cls, page: PageParam) -> '_SimpleCursor':
        if page.cursor:
            return decode_cursor_dataclass(page.cursor, cls)
        return cls(
            start_index=0,
            page_size=page.size,
            result_count=None,  # should be set when results are in
        )

    def next_cursor(self) -> str | None:
        if not self.result_count:
            return None
        _next = dataclasses.replace(self, start_index=(self.start_index + self.page_size))
        return (
            encode_cursor_dataclass(_next)
            if _next.is_valid_cursor()
            else None
        )

    def prev_cursor(self) -> str | None:
        _prev = dataclasses.replace(self, start_index=(self.start_index - self.page_size))
        return (
            encode_cursor_dataclass(_prev)
            if _prev.is_valid_cursor()
            else None
        )

    def first_cursor(self) -> str | None:
        if self.is_first_page():
            return None
        return encode_cursor_dataclass(dataclasses.replace(self, start_index=0))

    def is_first_page(self) -> bool:
        return self.start_index == 0

    def has_many_more(self) -> bool:
        return self.result_count == -1

    def max_index(self) -> int:
        return (
            self.MAX_INDEX
            if self.has_many_more()
            else min(self.result_count, self.MAX_INDEX)
        )

    def is_valid_cursor(self) -> bool:
        return 0 <= self.start_index < self.max_index()


@dataclasses.dataclass
class _CardsearchCursor(_SimpleCursor):
    random_sort: bool  # how to sort by relevance to nothingness? randomness!
    first_page_uuids: tuple[str, ...] = ()

    MAX_INDEX: ClassVar[int] = CARDSEARCH_MAX

    @classmethod
    def from_params(cls, params: CardsearchParams) -> '_CardsearchCursor':
        if params.page.cursor:
            return decode_cursor_dataclass(params.page.cursor, cls)
        return cls(
            start_index=0,
            page_size=params.page.size,
            result_count=None,  # should be set when results are in
            random_sort=(
                not params.sort_list
                and not params.cardsearch_textsegment_set
            ),
        )

    def cardsearch_start_index(self) -> int:
        if self.is_first_page() or not self.random_sort:
            return self.start_index
        return self.start_index - len(self.first_page_uuids)


class _PredicatePathWalker:
    WalkYield = tuple[tuple[str, ...], primitive_rdf.RdfObject]
    _visiting: set[str | frozenset]

    def __init__(self, tripledict: primitive_rdf.RdfTripleDictionary):
        self.tripledict = tripledict
        self._visiting = set()

    def walk_from_subject(self, iri_or_blanknode, last_path: tuple[str, ...] = ()) -> Iterable[WalkYield]:
        '''walk the graph from the given subject, yielding (pathkey, obj) for every reachable object
        '''
        with self._visit(iri_or_blanknode):
            _twopledict = (
                primitive_rdf.twopledict_from_twopleset(iri_or_blanknode)
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
                _text.unicode_value
                for _text in rdfdoc.q(iri, NAME_PROPERTIES)
                if isinstance(_text, primitive_rdf.Literal)
            ),
            title_text=frozenset(
                _text.unicode_value
                for _text in rdfdoc.q(iri, TITLE_PROPERTIES)
                if isinstance(_text, primitive_rdf.Literal)
            ),
            label_text=frozenset(
                _text.unicode_value
                for _text in rdfdoc.q(iri, LABEL_PROPERTIES)
                if isinstance(_text, primitive_rdf.Literal)
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
