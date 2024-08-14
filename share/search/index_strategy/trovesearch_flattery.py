from __future__ import annotations
import base64
from collections import abc, defaultdict
import contextlib
import dataclasses
import datetime
import functools
import json
import logging
import re
from typing import Iterable, ClassVar, Iterator

from django.conf import settings
from django.db.models import Exists, OuterRef
import elasticsearch8
from primitive_metadata import primitive_rdf as rdf

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
    PageParam,
    is_globpath,
)
from trove.trovesearch.search_response import (
    CardsearchResponse,
    ValuesearchResponse,
    TextMatchEvidence,
    CardsearchResult,
    ValuesearchResult,
    PropertypathUsage,
)
from trove.util.iris import get_sufficiently_unique_iri, is_worthwhile_iri
from trove.vocab.osfmap import is_date_property
from trove.vocab.namespaces import TROVE, FOAF, RDF, RDFS, DCTERMS, OWL, SKOS, OSFMAP


logger = logging.getLogger(__name__)


###
# constants

TITLE_PROPERTIES = (DCTERMS.title,)
NAME_PROPERTIES = (FOAF.name, OSFMAP.fileName)
LABEL_PROPERTIES = (RDFS.label, SKOS.prefLabel, SKOS.altLabel)
NAMELIKE_PROPERTIES = (*TITLE_PROPERTIES, *NAME_PROPERTIES, *LABEL_PROPERTIES)

SKIPPABLE_PROPERTIES = (
    OSFMAP.contains,  # too much, not helpful
    OWL.sameAs,  # handled special
)

VALUESEARCH_MAX = 234
CARDSEARCH_MAX = 9997

KEYWORD_LENGTH_MAX = 8191  # skip keyword terms that might exceed lucene's internal limit
# (see https://www.elastic.co/guide/en/elasticsearch/reference/current/ignore-above.html)
KEYWORD_MAPPING = {'type': 'keyword', 'ignore_above': KEYWORD_LENGTH_MAX}
FLATTENED_MAPPING = {'type': 'flattened', 'ignore_above': KEYWORD_LENGTH_MAX}
TEXT_MAPPING = {
    'type': 'text',
    'index_options': 'offsets',  # for highlighting
}
IRI_KEYWORD_MAPPING = {
    'type': 'object',
    'properties': {  # for indexing iri values two ways:
        'exact': KEYWORD_MAPPING,  # the exact iri value (e.g. "https://foo.example/bar/")
        'suffuniq': KEYWORD_MAPPING,  # "sufficiently unique" (e.g. "://foo.example/bar")
    },
}


###
# type aliases

Propertypath = tuple[str, ...]


###
# the strategy itself

class TrovesearchFlatteryIndexStrategy(Elastic8IndexStrategy):
    CURRENT_STRATEGY_CHECKSUM = ChecksumIri(
        checksumalgorithm_name='sha-256',
        salt='TrovesearchFlatteryIndexStrategy',
        hexdigest='...',
    )

    @classmethod
    def works_with_params(cls, params: CardsearchParams):
        return (
            not isinstance(params, ValuesearchParams)
            or (  # constraints on valuesearch:
                len(params.valuesearch_propertypath_set) == 1
                and not params.valuesearch_textsegment_set
                and all(
                    _filter.is_sameas_filter()
                    for _filter in params.valuesearch_filter_set
                )
            )
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
            'dynamic_templates': [
                {'dynamic_text_by_path': {
                    'path_match': 'dynamics.text_by_propertypath.*',
                    'mapping': TEXT_MAPPING,
                }},
                {'dynamic_text_by_depth': {
                    'path_match': 'dynamics.text_by_depth.*',
                    'mapping': TEXT_MAPPING,
                }},
                {'dynamic_date': {
                    'path_match': 'dynamics.date_by_propertypath.*',
                    'mapping': {
                        'type': 'date',
                        'format': 'strict_date_optional_time',
                    },
                }},
            ],
            'properties': {
                # simple keyword properties
                'indexcard_iri': KEYWORD_MAPPING,
                'indexcard_pk': KEYWORD_MAPPING,
                'suid': {
                    'type': 'object',
                    'properties': {
                        'source_config_label': KEYWORD_MAPPING,
                        'source_record_identifier': KEYWORD_MAPPING,
                    },
                },
                'focus_iri': IRI_KEYWORD_MAPPING,
                'propertypaths_present': KEYWORD_MAPPING,
                # flattened properties (dynamic sub-properties with keyword values)
                'iri_by_propertypath': FLATTENED_MAPPING,
                'iri_by_depth': FLATTENED_MAPPING,
                # dynamic properties (see dynamic_templates, above)
                'dynamics': {
                    'type': 'object',
                    'properties': {
                        'text_by_propertypath': {'type': 'object', 'dynamic': True},
                        'text_by_depth': {'type': 'object', 'dynamic': True},
                        'date_by_propertypath': {'type': 'object', 'dynamic': True},
                    },
                },
            },
        }

    # abstract method from Elastic8IndexStrategy
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
            _docbuilder = self._SourcedocBuilder(_indexcard_rdf)
            if not _docbuilder.should_skip():  # if skipped, will be deleted
                _index_action = self.build_index_action(
                    doc_id=str(_indexcard_rdf.indexcard.pk),
                    doc_source=_docbuilder.build(),
                )
                _remaining_indexcard_ids.discard(_indexcard_rdf.indexcard_id)
                yield _indexcard_rdf.indexcard_id, _index_action
        # delete any that don't have "latest" rdf and derived osfmap_json
        _leftovers = trove_db.Indexcard.objects.filter(id__in=_remaining_indexcard_ids)
        for _indexcard in _leftovers:
            yield _indexcard.id, self.build_delete_action(str(_indexcard.pk))

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
        def pls_handle_cardsearch(self, cardsearch_params: CardsearchParams) -> CardsearchResponse:
            _querybuilder = self.index_strategy._CardsearchQueryBuilder(cardsearch_params)
            _search_kwargs = _querybuilder.build()
            _cursor = _querybuilder.cardsearch_cursor
            if settings.DEBUG:
                logger.info(json.dumps(_search_kwargs, indent=2))
            try:
                _es8_response = self.index_strategy.es8_client.search(
                    index=self.indexname,
                    source=False,  # no need to get _source, identifiers are enough
                    docvalue_fields=['indexcard_iri'],
                    highlight={  # TODO: only one field gets highlighted?
                        'require_field_match': False,
                        'fields': {'dynamics.text_by_propertypath.*': {}},
                    },
                    **_search_kwargs,
                )
            except elasticsearch8.TransportError as error:
                raise exceptions.IndexStrategyError() from error  # TODO: error messaging
            return self.index_strategy._cardsearch_response(cardsearch_params, _es8_response, _cursor)

        # abstract method from IndexStrategy.SpecificIndex
        def pls_handle_valuesearch(self, valuesearch_params: ValuesearchParams) -> ValuesearchResponse:
            _querybuilder = self.index_strategy._ValuesearchQueryBuilder(valuesearch_params)
            _search_kwargs = _querybuilder.build()
            _cursor = _querybuilder.valuesearch_cursor
            if settings.DEBUG:
                logger.info(json.dumps(_search_kwargs, indent=2))
            try:
                _es8_response = self.index_strategy.es8_client.search(
                    index=self.indexname,
                    **_search_kwargs,
                )
            except elasticsearch8.TransportError as error:
                raise exceptions.IndexStrategyError() from error  # TODO: error messaging
            return self.index_strategy._valuesearch_response(valuesearch_params, _es8_response, _cursor)

    ###
    # building sourcedocs

    @dataclasses.dataclass
    class _SourcedocBuilder:
        '''build an elasticsearch sourcedoc for an rdf document
        '''
        indexcard_rdf: trove_db.IndexcardRdf
        indexcard: trove_db.Indexcard = dataclasses.field(init=False)
        rdfdoc: rdf.RdfTripleDictionary = dataclasses.field(init=False)
        focus_iri: str = dataclasses.field(init=False)

        def __post_init__(self) -> None:
            self.indexcard = self.indexcard_rdf.indexcard
            self.rdfdoc = rdf.RdfGraph(self.indexcard_rdf.as_rdf_tripledict())
            self.focus_iri = self.indexcard_rdf.focus_iri

        def should_skip(self) -> bool:
            _suid = self.indexcard.source_record_suid
            return (
                # skip cards that belong to an obsolete suid with a later duplicate
                _suid.has_forecompat_replacement()
                # ...or that are without some value for name/title/label
                or not any(self.rdfdoc.q(self.focus_iri, NAMELIKE_PROPERTIES))
            )

        def build(self) -> dict:
            _sourcedoc = {
                'indexcard_iri': self.indexcard.get_iri(),
                'indexcard_pk': str(self.indexcard.pk),
                'suid': {
                    'source_record_identifier': self.indexcard.source_record_suid.identifier,
                    'source_config_label': self.indexcard.source_record_suid.source_config.label,
                },
                'focus_iri': self._exact_and_suffuniq_iris(self.focus_iri, self._fullwalk),
                'propertypaths_present': self._propertypaths_present(self._fullwalk),
                'iri_by_propertypath': self._iris_by_propertypath(self._fullwalk),
                'iri_by_depth': self._iris_by_depth(self._fullwalk),
                'dynamics': {
                    'text_by_propertypath': self._texts_by_propertypath(self._fullwalk),
                    'text_by_depth': self._texts_by_depth(self._fullwalk),
                    'date_by_propertypath': self._dates_by_propertypath(self._fullwalk),
                },
            }
            logger.critical(json.dumps(_sourcedoc, indent=2))
            return _sourcedoc

        @functools.cached_property
        def _fullwalk(self) -> _GraphWalk:
            return _GraphWalk(self.rdfdoc, self.focus_iri)

        def _propertypaths_present(self, walk: _GraphWalk):
            return [
                propertypath_as_keyword(_path)
                for _path in walk.paths_walked
            ]

        def _iris_by_propertypath(self, walk: _GraphWalk):
            return {
                propertypath_as_field_name(_path): _suffuniq_iris(walk.iris_synonyms(_iris))
                for _path, _iris in walk.iri_values.items()
            }

        def _iris_by_depth(self, walk: _GraphWalk):
            _by_depth: dict[int, set[str]] = defaultdict(set)
            for _path, _iris in walk.iri_values.items():
                _by_depth[len(_path)].update(_iris)
            return {
                _depth_field_name(_depth): _suffuniq_iris(walk.iris_synonyms(_iris))
                for _depth, _iris in _by_depth.items()
            }

        def _texts_by_propertypath(self, walk: _GraphWalk):
            return {
                propertypath_as_field_name(_path): list(_value_set)
                for _path, _value_set in walk.text_values.items()
            }

        def _texts_by_depth(self, walk: _GraphWalk):
            _by_depth: dict[int, set[str]] = defaultdict(set)
            for (_path, _language_iris), _value_set in walk.text_values.items():
                _by_depth[len(_path)].update(_value_set)
            return {
                _depth_field_name(_depth): list(_value_set)
                for _depth, _value_set in _by_depth.items()
            }

        def _dates_by_propertypath(self, walk: _GraphWalk):
            return {
                propertypath_as_field_name(_path): list(_value_set)
                for _path, _value_set in walk.date_values.items()
            }

        def _exact_and_suffuniq_iris(self, iris: Iterable[str], walk: _GraphWalk):
            _synonyms = walk.iris_synonyms(iris)
            return {
                'exact': list(_synonyms),
                'suffuniq': _suffuniq_iris(_synonyms),
            }

    ###
    # building queries

    @dataclasses.dataclass
    class _CardsearchQueryBuilder:
        params: CardsearchParams

        def build(self):
            return {
                'query': self._cardsearch_query(),
                'aggs': self._cardsearch_aggs(),
                'sort': list(self._cardsearch_sorts()) or None,
                'from_': self.cardsearch_cursor.cardsearch_start_index(),
                'size': self.cardsearch_cursor.page_size,
            }

        @functools.cached_property
        def cardsearch_cursor(self):
            return _CardsearchCursor.from_cardsearch_params(self.params)

        @property
        def relevance_matters(self) -> bool:
            return not self.cardsearch_cursor.random_sort

        def _cardsearch_query(self) -> dict:
            _bool_query = {
                'filter': self._additional_cardsearch_filters(),
                'must': [],
                'must_not': [],
                'should': [],
            }
            # iri-keyword filters
            for _searchfilter in self.params.cardsearch_filter_set:
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
            # text-based queries
            for _boolkey, _textquery in self._cardsearch_text_boolparts():
                _bool_query[_boolkey].append(_textquery)
            return self._wrap_bool_query(_bool_query)

        def _wrap_bool_query(self, bool_query_innards) -> dict:
            # note: may modify bool_query_innards in-place
            _cursor = self.cardsearch_cursor
            if not _cursor or not _cursor.random_sort:
                # no need for randomness
                return {'bool': bool_query_innards}
            if not _cursor.first_page_pks:
                # independent random sample
                return {
                    'function_score': {
                        'query': {'bool': bool_query_innards},
                        'boost_mode': 'replace',
                        'random_score': {},  # default random_score is fast and unpredictable
                    },
                }
            _firstpage_filter = {'terms': {'indexcard_pk': _cursor.first_page_pks}}
            if _cursor.is_first_page():
                # returning to a first page previously visited
                bool_query_innards['filter'].append(_firstpage_filter)
                return {'bool': bool_query_innards}
            # get a subsequent page using reproducible randomness
            bool_query_innards['must_not'].append(_firstpage_filter)
            return {
                'function_score': {
                    'query': {'bool': bool_query_innards},
                    'boost_mode': 'replace',
                    'random_score': {
                        'seed': ''.join(_cursor.first_page_pks),
                        'field': 'indexcard_pk',
                    },
                },
            }

        def _additional_cardsearch_filters(self) -> list[dict]:
            return []  # for overriding

        def _cardsearch_aggs(self):
            _aggs = {}
            if self.params.related_property_paths:
                _aggs['agg_related_propertypath_usage'] = {'terms': {
                    'field': 'propertypaths_present',
                    'include': [
                        propertypath_as_keyword(_path)
                        for _path in self.params.related_property_paths
                    ],
                    'size': len(self.params.related_property_paths),
                }}
            return _aggs

        def _cardsearch_presence_query(self, search_filter) -> dict:
            return _any_query([
                self._cardsearch_path_presence_query(_path)
                for _path in search_filter.propertypath_set
            ])

        def _cardsearch_path_presence_query(self, path: Propertypath):
            return {'term': {'propertypaths_present': propertypath_as_keyword(path)}}

        def _cardsearch_iri_filter(self, search_filter) -> dict:
            _iris = _suffuniq_iris(search_filter.value_set)
            return _any_query([
                self._cardsearch_path_iri_query(_path, _iris)
                for _path in search_filter.propertypath_set
            ])

        def _cardsearch_path_iri_query(self, path, suffuniq_iris):
            _field = (
                f'iri_by_propertypath.{propertypath_as_field_name(path)}'
                if not is_globpath(path)
                else f'iri_by_depth.{_depth_field_name(len(path))}'
            )
            return {'terms': {_field: suffuniq_iris}}

        def _cardsearch_date_filter(self, search_filter):
            return _any_query([
                self._date_filter_for_path(_path, search_filter.operator, search_filter.value_set)
                for _path in search_filter.propertypath_set
            ])

        def _date_filter_for_path(self, path, filter_operator, value_set):
            _field = f'dynamics.date_by_propertypath.{propertypath_as_field_name(path)}'
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

        def _cardsearch_sorts(self):
            for _sortparam in self.params.sort_list:
                _pathfield = propertypath_as_field_name((_sortparam.property_iri,))
                _fieldpath = f'dynamics.date_by_propertypath.{_pathfield}'
                _order = 'desc' if _sortparam.descending else 'asc'
                yield {_fieldpath: _order}

        def _cardsearch_text_boolparts(self) -> Iterator[tuple[str, dict]]:
            for _textsegment in self.params.cardsearch_textsegment_set:
                if _textsegment.is_negated:
                    yield 'must_not', self._exact_text_query(_textsegment)
                elif not _textsegment.is_fuzzy:
                    yield 'must', self._exact_text_query(_textsegment)
                else:
                    yield 'must', self._fuzzy_text_must_query(_textsegment)
                    # if self.relevance_matters:
                    #     yield 'should', self._fuzzy_text_should_query(_textsegment)

        def _text_field_name(self, propertypath: Propertypath):
            return (
                f'dynamics.text_by_propertypath.{propertypath_as_field_name(propertypath)}'
                if not is_globpath(propertypath)
                else f'dynamics.text_by_depth.{_depth_field_name(len(propertypath))}'
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

    class _ValuesearchQueryBuilder(_CardsearchQueryBuilder):
        params: ValuesearchParams

        # override _CardsearchQueryBuilder
        def build(self):
            if self._is_date_valuesearch():
                _aggs = self._valuesearch_date_aggs()
            elif self._can_use_nonnested_aggs():
                _aggs = self._valuesearch_nonnested_iri_aggs()
            else:
                _aggs = self._valuesearch_nested_iri_aggs()
            return dict(
                query=self._cardsearch_query(),
                size=0,  # ignore cardsearch hits; just want the aggs
                aggs=_aggs,
            )

        @functools.cached_property
        def valuesearch_cursor(self):
            return _SimpleCursor.from_page_param(self.params.page)

        # override _CardsearchQueryBuilder
        @property
        def relevance_matters(self) -> bool:
            return False  # valuesearch always ordered by count

        def _is_date_valuesearch(self) -> bool:
            return all(
                is_date_property(_path[-1])
                for _path in self.params.valuesearch_propertypath_set
            )

        def _can_use_nonnested_aggs(self):
            return (
                len(self.params.valuesearch_propertypath_set) == 1
                and not self.params.valuesearch_textsegment_set
                and all(
                    _filter.is_sameas_filter()
                    for _filter in self.params.valuesearch_filter_set
                )
            )

        def _additional_cardsearch_filters(self) -> list[dict]:
            return [{'terms': {'propertypaths_present': [
                propertypath_as_keyword(_path)
                for _path in self.params.valuesearch_propertypath_set
            ]}}]

        def _valuesearch_nonnested_iri_aggs(self):
            (_propertypath,) = self.params.valuesearch_propertypath_set
            _field = f'iri_by_propertypath.{propertypath_as_field_name(_propertypath)}'
            _terms_agg: dict = {'field': _field}
            _specific_iris = list(set(self.params.valuesearch_iris()))
            if _specific_iris:
                _terms_agg['include'] = _specific_iris
                _terms_agg['size'] = len(_specific_iris)
            return {'agg_valuesearch': {'terms': _terms_agg}}

        def _valuesearch_nested_iri_aggs(self):
            raise NotImplementedError('_valuesearch_nested_iri_aggs')
            _nested_iri_bool = {
                'filter': ...,
                'must': [],
                'must_not': [],
                'should': [],
            }
            _nested_terms_agg = {
                'field': 'nested_iri.iri_value',
                # WARNING: terribly inefficient pagination (part one)
                'size': cursor.start_index + cursor.page_size + 1,
            }
            _specific_iris = list(self.params.valuesearch_iris())
            if _specific_iris:
                _nested_iri_bool['filter'].append({'terms': {
                    'nested_iri.iri_value': _specific_iris,
                }})
                _nested_terms_agg['size'] = len(_specific_iris)
                _nested_terms_agg['include'] = _specific_iris
            _type_iris = list(self.params.valuesearch_type_iris())
            if _type_iris:
                _nested_iri_bool['filter'].append({'terms': {
                    'nested_iri.type_iri': _type_iris,
                }})
            _textq_builder = self._SimpleTextQueryBuilder('nested_iri.value_namelike_text')
            for _textsegment in self.params.valuesearch_textsegment_set:
                for _boolkey, _textqueries in _textq_builder.textsegment_boolparts(_textsegment).items():
                    _nested_iri_bool[_boolkey].extend(_textqueries)
            return {
                'in_nested_iri': {
                    'nested': {'path': 'nested_iri'},
                    'aggs': {
                        'value_at_propertypath': {
                            'filter': {'bool': _nested_iri_bool},
                            'aggs': {
                                'agg_iri_values': {
                                    'terms': _nested_terms_agg,
                                    'aggs': {
                                        'type_iri': {'terms': {
                                            'field': 'nested_iri.type_iri',
                                        }},
                                        'name_text': {'terms': {
                                            'field': 'nested_iri.name_text.raw',
                                        }},
                                        'title_text': {'terms': {
                                            'field': 'nested_iri.title_text.raw',
                                        }},
                                        'label_text': {'terms': {
                                            'field': 'nested_iri.label_text.raw',
                                        }},
                                    },
                                },
                            },
                        },
                    },
                },
            }

        def _valuesearch_date_aggs(self):
            _aggs = {
                'in_nested_date': {
                    'nested': {'path': 'nested_date'},
                    'aggs': {
                        'value_at_propertypath': {
                            'filter': {'terms': {
                                'nested_date.suffuniq_path_from_focus': [
                                    propertypath_as_keyword(_path)
                                    for _path in self.params.valuesearch_propertypath_set
                                ],
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

    ###
    # normalizing search responses

    def _valuesearch_response(
        self,
        valuesearch_params: ValuesearchParams,
        es8_response: dict,
        cursor: '_SimpleCursor',
    ) -> ValuesearchResponse:
        _iri_aggs = es8_response['aggregations'].get('in_nested_iri')
        if _iri_aggs:
            _buckets = _iri_aggs['value_at_propertypath']['agg_iri_values']['buckets']
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

    def _valuesearch_iri_result(self, iri_bucket) -> ValuesearchResult:
        return ValuesearchResult(
            value_iri=iri_bucket['key'],
            value_type=_bucketlist(iri_bucket['type_iri']),
            name_text=_bucketlist(iri_bucket['name_text']),
            title_text=_bucketlist(iri_bucket['title_text']),
            label_text=_bucketlist(iri_bucket['label_text']),
            match_count=iri_bucket['doc_count'],
        )

    def _valuesearch_date_result(self, date_bucket) -> ValuesearchResult:
        return ValuesearchResult(
            value_iri=None,
            value_value=date_bucket['key_as_string'],
            label_text=(date_bucket['key_as_string'],),
            match_count=date_bucket['doc_count'],
        )

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
                cursor.result_count += len(cursor.first_page_pks)
        _results = []
        for _es8_hit in es8_response['hits']['hits']:
            _card_iri = _es8_hit['fields']['indexcard_iri'][0]
            _results.append(CardsearchResult(
                card_iri=_card_iri,
                card_pk=_es8_hit['_id'],
                text_match_evidence=list(self._gather_textmatch_evidence(_card_iri, _es8_hit)),
            ))
        if cursor.is_first_page() and cursor.first_page_pks:
            # revisiting first page; reproduce original random order
            _ordering_by_id = {
                _id: _i
                for (_i, _id) in enumerate(cursor.first_page_pks)
            }
            _results.sort(key=lambda _r: _ordering_by_id[_r.card_pk])
        else:
            _should_start_reproducible_randomness = (
                cursor.random_sort
                and cursor.is_first_page()
                and not cursor.first_page_pks
                and not cursor.has_many_more()
                and any(
                    not _filter.is_type_filter()  # look for a non-default filter
                    for _filter in cardsearch_params.cardsearch_filter_set
                )
            )
            if _should_start_reproducible_randomness:
                cursor.first_page_pks = tuple(_result.card_pk for _result in _results)
        _relatedproperty_list: list[PropertypathUsage] = []
        if cardsearch_params.related_property_paths:
            _relatedproperty_list.extend(
                PropertypathUsage(property_path=_path, usage_count=0)
                for _path in cardsearch_params.related_property_paths
            )
            _relatedproperty_by_path = {
                _result.property_path: _result
                for _result in _relatedproperty_list
            }
            for _bucket in es8_response['aggregations']['agg_related_propertypath_usage']['buckets']:
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
# assorted helper functions

def propertypath_as_keyword(path: Propertypath) -> str:
    return json.dumps(path if is_globpath(path) else [
        get_sufficiently_unique_iri(_iri)
        for _iri in path
    ])


def propertypath_as_field_name(path: Propertypath) -> str:
    _path_keyword = propertypath_as_keyword(path)
    return base64.urlsafe_b64encode(_path_keyword.encode()).decode()


def _suffuniq_iris(iris: Iterable[str]) -> list[str]:
    # deduplicates, may reorder
    return list({
        get_sufficiently_unique_iri(_iri)
        for _iri in iris
    })


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


def _parse_path_field_name(path_field_name: str) -> Propertypath:
    # inverse of propertypath_as_field_name
    _list = json.loads(base64.urlsafe_b64decode(path_field_name.encode()).decode())
    assert isinstance(_list, list)
    assert all(isinstance(_item, str) for _item in _list)
    return tuple(_list)


def _any_query(queries: abc.Collection[dict]):
    if len(queries) == 1:
        (_query,) = queries
        return _query
    return {'bool': {'should': list(queries), 'minimum_should_match': 1}}


def _pathset_as_nestedvalue_filter(propertypath_set: frozenset[Propertypath], nested_path: str):
    _suffuniq_iri_paths = []
    _glob_path_lengths = []
    for _path in propertypath_set:
        if is_globpath(_path):
            _glob_path_lengths.append(len(_path))
        else:
            _suffuniq_iri_paths.append(propertypath_as_keyword(_path))
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
    first_page_pks: tuple[str, ...] = ()

    MAX_INDEX: ClassVar[int] = CARDSEARCH_MAX

    @classmethod
    def from_cardsearch_params(cls, params: CardsearchParams) -> '_CardsearchCursor':
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
        return self.start_index - len(self.first_page_pks)

    def first_cursor(self) -> str | None:
        if self.random_sort and not self.first_page_pks:
            return None
        return super().prev_cursor()

    def prev_cursor(self) -> str | None:
        if self.random_sort and not self.first_page_pks:
            return None
        return super().prev_cursor()


@dataclasses.dataclass
class _GraphWalk:
    rdfdoc: rdf.RdfGraph
    focus_iri: str
    recursive: bool = True
    iri_values: dict[Propertypath, set[str]] = dataclasses.field(
        default_factory=lambda: defaultdict(set),
    )
    text_values: dict[Propertypath, set[rdf.Literal]] = dataclasses.field(
        default_factory=lambda: defaultdict(set),
    )
    date_values: dict[Propertypath, set[datetime.date]] = dataclasses.field(
        default_factory=lambda: defaultdict(set),
    )
    paths_walked: set[Propertypath] = dataclasses.field(default_factory=set)
    _visiting: set[str] = dataclasses.field(default_factory=set)

    def __post_init__(self):
        for _walk_path, _walk_obj in self._walk_from_subject(self.focus_iri):
            self.paths_walked.add(_walk_path)
            if isinstance(_walk_obj, str):
                self.iri_values[_walk_path].add(_walk_obj)
            elif isinstance(_walk_obj, datetime.date):
                self.date_values[_walk_path].add(_walk_obj)
            elif is_date_property(_walk_path[-1]):
                try:
                    _parsed_date = datetime.date.fromisoformat(_walk_obj.unicode_value)
                except ValueError:
                    logger.debug('skipping malformatted date "%s"', _walk_obj.unicode_value)
                else:
                    self.date_values[_walk_path].add(_parsed_date)
            elif isinstance(_walk_obj, rdf.Literal):
                self.text_values[_walk_path].add(_walk_obj.unicode_value)

    def shortwalk(self, from_iri: str) -> _GraphWalk:
        return _GraphWalk(
            self.rdfdoc,
            self.focus_iri,
            recursive=False,
        )

    def _walk_from_subject(
        self,
        iri_or_blanknode: str | rdf.Blanknode,
        path_so_far: tuple[str, ...] = (),
    ) -> Iterator[tuple[Propertypath, rdf.RdfObject]]:
        '''walk the graph from the given subject, yielding (pathkey, obj) for every reachable object
        '''
        with self._visit(iri_or_blanknode):
            _twoples = (
                iri_or_blanknode
                if isinstance(iri_or_blanknode, frozenset)
                else self.rdfdoc.tripledict.get(iri_or_blanknode, {})
            )
            for _next_steps, _obj in walk_twoples(_twoples):
                _path = (*path_so_far, *_next_steps)
                yield (_path, _obj)
                if self.recursive and isinstance(_obj, str) and (_obj not in self._visiting):
                    # step further for iri or blanknode
                    yield from self._walk_from_subject(_obj, path_so_far=_path)

    def iri_synonyms(self, iri: str) -> set[str]:
        # note: extremely limited inference -- assumes objects of owl:sameAs are not used as subjects
        _synonyms = (
            _synonym
            for _synonym in self.rdfdoc.q(iri, OWL.sameAs)
            if is_worthwhile_iri(_synonym)
        )
        return {iri, *_synonyms}

    def iris_synonyms(self, iris: Iterable[str]) -> set[str]:
        return {
            _synonym
            for _iri in iris
            for _synonym in self.iri_synonyms(_iri)
        }

    @contextlib.contextmanager
    def _visit(self, focus_obj):
        assert focus_obj not in self._visiting
        self._visiting.add(focus_obj)
        yield
        self._visiting.discard(focus_obj)


def walk_twoples(
    twoples: rdf.RdfTwopleDictionary | rdf.Blanknode,
) -> Iterator[tuple[Propertypath, rdf.RdfObject]]:
    if isinstance(twoples, frozenset):
        _iter_twoples = (
            (_pred, _obj)
            for _pred, _obj in twoples
            if _pred not in SKIPPABLE_PROPERTIES
        )
    else:
        _iter_twoples = (
            (_pred, _obj)
            for _pred, _obj_set in twoples.items
            if _pred not in SKIPPABLE_PROPERTIES
            for _obj in _obj_set
        )
    for _pred, _obj in _iter_twoples:
        _path = (_pred,)
        if isinstance(_obj, frozenset):
            for _innerpath, _innerobj in walk_twoples(_obj):
                yield (
                    (*_path, *_innerpath),
                    _innerobj,
                )
        else:
            yield (_path, _obj)
