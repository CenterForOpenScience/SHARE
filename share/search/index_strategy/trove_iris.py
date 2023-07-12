import contextlib
import datetime
import json
import logging

import elasticsearch8
import gather

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
    # TextMatchEvidence,
    # SearchResult,
)
# from share.search.trovesearch_gathering import TROVE
from share.util.checksum_iri import ChecksumIri
from trove import models as trove_db
from trove.vocab.osfmap import OSFMAP, DCTERMS


logger = logging.getLogger(__name__)


class TroveIrisIndexStrategy(Elastic8IndexStrategy):
    CURRENT_STRATEGY_CHECKSUM = ChecksumIri(
        checksumalgorithm_name='sha-256',
        salt='TroveIrisIndexStrategy',
        hexdigest='11c504a0c6367791993dd54de98c7dbed00547d188c94412bdb7d7609c644a5d',
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
                'focustype_iri': {'type': 'keyword'},
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
                            'index_prefixes': {  # support prefix query
                                'min_chars': 3,
                                'max_chars': 10,
                            },
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
            elif isinstance(_obj, gather.Text):
                if _is_date_property(_property_path[-1]):
                    _nested_dates.setdefault(_property_path, set()).add(_obj.unicode_text)
                else:
                    _nested_texts.setdefault(_property_path, set()).add(_obj)
        return {
            'focus_iri': [
                _identifier.as_iri()
                for _identifier in indexcard_rdf.indexcard.focus_identifier_set.all()
            ],
            'focustype_iri': [
                _identifier.as_iri()
                for _identifier in indexcard_rdf.indexcard.focustype_identifier_set.all()
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
            .prefetch_related(
                'indexcard__focus_identifier_set',
                'indexcard__focustype_identifier_set',
            )
        )
        _remaining_indexcard_ids = set(messages_chunk.target_ids_chunk)
        for _indexcard_rdf in _indexcard_rdf_qs:
            _indexcard_id = _indexcard_rdf.indexcard_id
            _remaining_indexcard_ids.discard(_indexcard_id)
            _index_action = self.build_index_action(
                doc_id=_indexcard_rdf.indexcard.uuid,
                doc_source=self._build_sourcedoc(_indexcard_rdf),
            )
            yield _indexcard_id, _index_action
        # delete any that don't have any of the expected card
        _leftovers = (
            trove_db.Indexcard.objects
            .filter(id__in=_remaining_indexcard_ids)
            .values_list('id', 'uuid')
        )
        for _indexcard_id, _indexcard_uuid in _leftovers:
            yield _indexcard_id, self.build_delete_action(_indexcard_uuid)

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
            return dict(_es8_response)  # TODO

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
                else:  # before, after
                    _bool_query['filter'].append(self._date_filter(_search_filter))
            for _textsegment in search_params.cardsearch_textsegment_set:
                if _textsegment.is_negated:
                    _bool_query['must_not'].append(
                        self._excluded_text_query(_textsegment)
                    )
                else:
                    if _textsegment.is_fuzzy:
                        _bool_query['must'].append(self._fuzzy_text_query(_textsegment))
                    else:
                        _bool_query['must'].append(self._exact_text_query(_textsegment))
            logger.critical(f'>>>bool: {json.dumps(_bool_query, indent=2)}')
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
            _queryname = (
                # 'match_phrase_prefix'
                'match_phrase'
                if textsegment.is_openended
                else 'match_phrase'
            )
            return {'nested': {
                'path': 'nested_text',
                'query': {_queryname: {
                    'nested_text.text_value': {
                        'query': textsegment.text,
                    },
                }},
                'inner_hits': self._text_inner_hits(),
            }}

        def _fuzzy_text_query(self, textsegment: Textsegment):
            if textsegment.is_openended:
                (*_nonlast_words, _last_word) = textsegment.words()
                _fuzzybool = {
                    'minimum_should_match': 1,
                    'should': [
                        {'prefix': {
                            'nested_text.text_value': {
                                'value': _last_word,
                            },
                        }},
                        {'match': {
                            'nested_text.text_value': {
                                'query': _last_word,
                                'fuzziness': 'AUTO',
                            },
                        }},
                    ],
                }
                if _nonlast_words:
                    _fuzzybool['must'] = {'match': {
                        'nested_text.text_value': {
                            'query': ' '.join(_nonlast_words),
                            'fuzziness': 'AUTO',
                        },
                    }}
                _query = {'bool': _fuzzybool}
            else:  # not openended
                _query = {'match': {
                    'nested_text.text_value': {
                        'query': textsegment.text,
                        'fuzziness': 'AUTO',
                    },
                }}
            return {'nested': {
                'path': 'nested_text',
                'query': _query,
                'inner_hits': self._text_inner_hits(),
            }}

        def _text_inner_hits(self):
            return {
                'highlight': {'fields': {'nested_text.text_value': {}}},
                '_source': False,  # _source is expensive for nested docs
                'docvalue_fields': [
                    'nested_text.property_path',
                    'nested_text.language_iri',
                ],
            }


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
    def __init__(self, tripledict: gather.RdfTripleDictionary):
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

    def _walk_twopledict(self, focus_twopledict: gather.RdfTwopleDictionary):
        for _predicate_iri, _obj_set in focus_twopledict.items():
            with self._pathstep(_predicate_iri) as _pathtuple:
                for _obj in _obj_set:
                    if isinstance(_obj, gather.Text):
                        yield (_pathtuple, _obj)
                        _next_twopledict = None
                    elif isinstance(_obj, str):  # IRI
                        yield (_pathtuple, _obj)
                        _next_twopledict = (
                            None
                            if _obj in self._visiting
                            else self.tripledict.get(_obj)
                        )
                    elif isinstance(_obj, frozenset):
                        _next_twopledict = gather.twopleset_as_twopledict(_obj)
                    else:
                        continue
                    if _next_twopledict and (_obj not in self._visiting):
                        with self._visit(_obj):
                            yield from self._walk_twopledict(_next_twopledict)
