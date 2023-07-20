import contextlib
import datetime
import json
import logging
import uuid

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
)
from share.search.search_response import (
    CardsearchResponse,
    PropertysearchResponse,
    ValuesearchResponse,
    TextMatchEvidence,
    SearchResult,
)
from share.util.checksum_iri import ChecksumIri
from trove import models as trove_db
from trove.vocab.namespaces import TROVE, OSFMAP, DCTERMS


logger = logging.getLogger(__name__)


class TroveIrisIndexStrategy(Elastic8IndexStrategy):
    CURRENT_STRATEGY_CHECKSUM = ChecksumIri(
        checksumalgorithm_name='sha-256',
        salt='TroveIrisIndexStrategy',
        hexdigest='23dc9625d9367342aab86f53c07ecdba2b540383ce8f40683e9013629a22f330',
    )

    @property
    def supported_message_types(self):
        return {
            messages.MessageType.UPDATE_INDEXCARD,
            messages.MessageType.BACKFILL_INDEXCARD,
        }

    def index_settings(self):
        return {}

    def index_mappings(self):
        return {
            'dynamic': 'false',
            'properties': {
                'focus_iri': {'type': 'keyword'},
                # 'included_predicate_iri': {'type': 'keyword'},
                # 'included_resource_iri': {'type': 'keyword'},
                # 'included_vocab_iri': {'type': 'keyword'},
                'nested_iri': {
                    'type': 'nested',
                    'dynamic': 'strict',
                    'properties': {
                        'property_path': {'type': 'keyword'},
                        'iri_value': {'type': 'keyword'},
                    },
                },
                'nested_date': {
                    'type': 'nested',
                    'dynamic': 'strict',
                    'properties': {
                        'property_path': {'type': 'keyword'},
                        'date_value': {
                            'type': 'date',
                            'format': 'strict_date_optional_time',
                        },
                    },
                },
                'nested_text': {
                    'type': 'nested',
                    'dynamic': 'strict',
                    'properties': {
                        'property_path': {'type': 'keyword'},
                        'language_iri': {'type': 'keyword'},
                        'text_value': {
                            'type': 'text',
                            'index_options': 'offsets',  # for faster highlighting
                            'store': True,  # avoid loading _source to render highlights
                        },
                    },
                },
            },
        }

    def _build_sourcedoc(self, indexcard_rdf):
        _tripledict = indexcard_rdf.as_rdf_tripledict()
        _nested_iris = {}
        _nested_dates = {}
        _nested_texts = {}
        for _property_path, _obj in _PropertyPathWalker(_tripledict).from_focus(indexcard_rdf.focus_iri):
            if isinstance(_obj, str):
                _nested_iris.setdefault(_property_path, set()).add(_obj)
            elif isinstance(_obj, primitive_rdf.Text):
                if _is_date_property(_property_path[-1]):
                    _nested_dates.setdefault(_property_path, set()).add(_obj.unicode_text)
                else:
                    _nested_texts.setdefault(_property_path, set()).add(_obj)
        return {
            'focus_iri': [
                _identifier.as_iri()
                for _identifier in indexcard_rdf.indexcard.focus_identifier_set.all()
            ],
            'nested_iri': [
                {
                    'property_path': _property_path_as_keyword(_propertypath),
                    'iri_value': list(_value_set),
                }
                for _propertypath, _value_set in _nested_iris.items()
            ],
            'nested_date': [
                {
                    'property_path': _property_path_as_keyword(_propertypath),
                    'date_value': list(_value_set),
                }
                for _propertypath, _value_set in _nested_dates.items()
            ],
            'nested_text': [
                {
                    'property_path': _property_path_as_keyword(_propertypath),
                    'language_iri': _value.language_iri,
                    'text_value': _value.unicode_text,
                }
                for _propertypath, _value_set in _nested_texts.items()
                for _value in _value_set
            ],
        }

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
        # delete any that don't have any of the expected card
        _leftovers = (
            trove_db.Indexcard.objects
            .filter(id__in=_remaining_indexcard_ids)
        )
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
                    query=self._cardsearch_query(cardsearch_params),
                    # highlight={'fields': {'nested_text.text_value': {}}},
                    source=False,  # no need to get _source; _id is enough
                )
            except elasticsearch8.TransportError as error:
                raise exceptions.IndexStrategyError() from error  # TODO: error messaging
            return self._cardsearch_response(cardsearch_params, _es8_response)

        def pls_handle_propertysearch(self, propertysearch_params: PropertysearchParams) -> PropertysearchResponse:
            raise NotImplementedError

        def pls_handle_valuesearch(self, valuesearch_params: ValuesearchParams) -> ValuesearchResponse:
            raise NotImplementedError

        def _cardsearch_query(self, search_params):
            _bool_query = {
                'filter': [],
                'must': [],
                'must_not': [],
                'should': [],
            }
            for _search_filter in search_params.cardsearch_filter_set:
                if _search_filter.operator == SearchFilter.FilterOperator.NONE_OF:
                    _bool_query['must_not'].append(self._iri_filter(_search_filter))
                elif _search_filter.operator == SearchFilter.FilterOperator.ANY_OF:
                    _bool_query['filter'].append(self._iri_filter(_search_filter))
                elif _search_filter.operator.is_date_operator():
                    _bool_query['filter'].append(self._date_filter(_search_filter))
                else:
                    raise ValueError(f'unknown filter operator {_search_filter.operator}')
            _fuzzysegments = []
            for _textsegment in search_params.cardsearch_textsegment_set:
                if _textsegment.is_negated:
                    _bool_query['must_not'].append(
                        self._excluded_text_query(_textsegment)
                    )
                elif _textsegment.is_fuzzy:
                    _fuzzysegments.append(_textsegment)
                else:
                    _bool_query['must'].append(self._exact_text_query(_textsegment))
            if _fuzzysegments:
                _bool_query['must'].append(self._fuzzy_text_must_query(_fuzzysegments))
                _bool_query['should'].extend(self._fuzzy_text_should_queries(_fuzzysegments))
            return {'bool': _bool_query}

        def _iri_filter(self, search_filter) -> dict:
            _propertypath_keyword = _property_path_as_keyword(search_filter.property_path)
            return {'nested': {
                'path': 'nested_iri',
                'query': {'bool': {
                    'filter': [
                        {'term': {'nested_iri.property_path': _propertypath_keyword}},
                        {'terms': {'nested_iri.iri_value': list(search_filter.value_set)}},
                    ],
                }},
            }}

        def _date_filter(self, search_filter):
            if search_filter.operator == SearchFilter.FilterOperator.BEFORE:
                _range_op = 'lt'
                _value = min(search_filter.value_set)  # lean on that isoformat
            elif search_filter.operator == SearchFilter.FilterOperator.AFTER:
                _range_op = 'gte'
                _value = max(search_filter.value_set)  # lean on that isoformat
            else:
                raise ValueError(f'invalid date filter operator (got {search_filter.operator})')
            _date_value = datetime.datetime.fromisoformat(_value).date()
            _propertypath_keyword = _property_path_as_keyword(search_filter.property_path)
            return {'nested': {
                'path': 'nested_date',
                'query': {'bool': {
                    'filter': [
                        {'term': {'nested_date.property_path': _propertypath_keyword}},
                        {'range': {'nested_date.date_value': {
                            _range_op: f'{_date_value}||/d',  # round to the day
                        }}},
                    ],
                }},
            }}

        def _excluded_text_query(self, textsegment: Textsegment):
            return {'nested': {
                'path': 'nested_text',
                'query': {'match_phrase': {
                    'nested_text.text_value': {
                        'query': textsegment.text,
                    },
                }},
            }}

        def _exact_text_query(self, textsegment: Textsegment):
            # TODO: textsegment.is_openended (prefix query)
            _query = {'match_phrase': {
                'nested_text.text_value': {
                    'query': textsegment.text,
                },
            }}
            return {'nested': {
                'path': 'nested_text',
                'query': _query,
                'inner_hits': self._text_inner_hits(),
            }}

        def _fuzzy_text_must_query(self, textsegments: list[Textsegment]):
            # TODO: textsegment.is_openended (prefix query)
            _query = {'match': {
                'nested_text.text_value': {
                    'query': ' '.join(
                        _textsegment.text
                        for _textsegment in textsegments
                    ),
                    'fuzziness': 'AUTO',
                },
            }}
            return {'nested': {
                'path': 'nested_text',
                'query': _query,
                'inner_hits': self._text_inner_hits()
            }}

        def _fuzzy_text_should_queries(self, textsegments: list[Textsegment]):
            for _textsegment in textsegments:
                yield {'nested': {
                    'path': 'nested_text',
                    'query': {'match_phrase': {
                        'nested_text.text_value': {
                            'query': _textsegment.text,
                            'slop': len(_textsegment.words()),
                        },
                    }}
                }}

        def _text_inner_hits(self, *, highlight_query=None):
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
                    'nested_text.property_path',
                    'nested_text.language_iri',
                ],
            }

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
                _results.append(SearchResult(
                    card_iri=_card_iri,
                    text_match_evidence=list(self._gather_textmatch_evidence(_es8_hit)),
                ))
            return CardsearchResponse(
                total_result_count=_total,
                search_result_page=_results,
                related_propertysearch_set=(),
            )

        def _gather_textmatch_evidence(self, es8_hit):
            for _innerhit_group in es8_hit['inner_hits'].values():
                for _innerhit in _innerhit_group['hits']['hits']:
                    _property_path = tuple(
                        json.loads(_innerhit['fields']['nested_text.property_path'][0]),
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


###
# local utils

def _property_path_as_keyword(property_path) -> str:
    assert isinstance(property_path, (list, tuple))
    return json.dumps(property_path)


def _is_date_property(property_iri):
    # TODO: better inference (rdfs:range?)
    return property_iri in {
        DCTERMS.date,
        DCTERMS.available,
        DCTERMS.created,
        DCTERMS.modified,
        DCTERMS.dateCopyrighted,
        DCTERMS.dateSubmitted,
        DCTERMS.dateAccepted,
        OSFMAP.withdrawn,
    }


class _PropertyPathWalker:
    def __init__(self, tripledict: primitive_rdf.RdfTripleDictionary):
        self.tripledict = tripledict
        self._visiting = set()
        self._path_so_far = []

    def from_focus(self, focus_iri: str):
        with self._visit(focus_iri):
            _focus_twopledict = self.tripledict.get(focus_iri, {})
            yield from self._walk_twopledict(_focus_twopledict)

    @contextlib.contextmanager
    def _pathstep(self, predicate_iri):
        self._path_so_far.append(predicate_iri)
        yield tuple(self._path_so_far)
        self._path_so_far.pop()

    @contextlib.contextmanager
    def _visit(self, focus_obj):
        assert focus_obj not in self._visiting
        self._visiting.add(focus_obj)
        yield
        self._visiting.discard(focus_obj)

    def _walk_twopledict(self, focus_twopledict: primitive_rdf.RdfTwopleDictionary):
        for _predicate_iri, _obj_set in focus_twopledict.items():
            with self._pathstep(_predicate_iri) as _pathtuple:
                for _obj in _obj_set:
                    _next_twopledict = None
                    if isinstance(_obj, primitive_rdf.Text):
                        yield (_pathtuple, _obj)
                    elif isinstance(_obj, str):  # IRI
                        yield (_pathtuple, _obj)
                        if _obj not in self._visiting:
                            _next_twopledict = self.tripledict.get(_obj)
                    elif isinstance(_obj, frozenset):
                        if _obj not in self._visiting:
                            _next_twopledict = primitive_rdf.twopleset_as_twopledict(_obj)
                    if _next_twopledict:
                        with self._visit(_obj):
                            yield from self._walk_twopledict(_next_twopledict)
