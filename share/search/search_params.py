import dataclasses
import enum
import itertools
import logging
import typing

from share.search import exceptions
from share.search.jsonapi_queryparams import (
    JsonapiQueryparamName,
    split_queryparam_value,
    queryparams_from_querystring,
)


logger = logging.getLogger(__name__)


###
# special characters in search text:
NEGATE_WORD_OR_PHRASE = '-'
DOUBLE_QUOTATION_MARK = '"'


###
# search api parameters

@dataclasses.dataclass(frozen=True)
class Textsegment:
    text: str
    is_fuzzy: bool = True
    is_negated: bool = False
    is_openended: bool = False

    def __post_init__(self):
        if self.is_negated and self.is_fuzzy:
            raise ValueError(f'{self}: cannot have both is_negated and is_fuzzy')

    @classmethod
    def from_str(cls, text: str) -> typing.Iterable['Textsegment']:
        '''parse search text into words and quoted phrases
        '''
        _in_quotes = False
        _last_quote_prefix = None
        _text_remaining = text
        while _text_remaining:
            (
                _text_chunk,
                _quote_mark,
                _text_remaining,
            ) = _text_remaining.partition(DOUBLE_QUOTATION_MARK)
            if _text_chunk:
                _is_openended = not (_quote_mark or _text_remaining)
                if _in_quotes:
                    yield cls(
                        text=_text_chunk,
                        is_fuzzy=False,
                        is_negated=(_last_quote_prefix == NEGATE_WORD_OR_PHRASE),
                        is_openended=_is_openended,
                    )
                else:
                    yield from cls._from_fuzzy_text(
                        _text_chunk,
                        is_openended=_is_openended,
                    )
            if _quote_mark:
                if _in_quotes:  # end quote
                    _in_quotes = False
                    _last_quote_prefix = None
                else:  # begin quote
                    _in_quotes = True
                    _last_quote_prefix = _text_chunk[-1:]

    @classmethod
    def _from_fuzzy_text(cls, text_chunk: str, is_openended: bool):
        logger.critical(f'from fuzzy: {text_chunk}')
        _all_wordgroups = (
            (_word_negated, list(_words))
            for (_word_negated, _words) in itertools.groupby(
                text_chunk.split(),
                key=lambda word: word.startswith(NEGATE_WORD_OR_PHRASE),
            )
        )
        (*_wordgroups, (_lastgroup_negated, _lastgroup_words)) = _all_wordgroups
        for _word_negated, _words in _wordgroups:
            yield from cls._from_fuzzy_wordgroup(
                _word_negated,
                _words,
                is_openended=False,
            )
        yield from cls._from_fuzzy_wordgroup(
            _lastgroup_negated,
            _lastgroup_words,
            is_openended=is_openended,
        )

    @classmethod
    def _from_fuzzy_wordgroup(cls, word_negated: bool, words: typing.Iterable[str], *, is_openended=False):
        if word_negated:
            for _word in words:
                yield cls(
                    text=_word[len(NEGATE_WORD_OR_PHRASE):],  # remove prefix
                    is_fuzzy=False,
                    is_negated=True,
                    is_openended=False,
                )
        else:  # nothing negated; keep the phrase in one fuzzy segment
            yield cls(
                text=' '.join(words),
                is_fuzzy=True,
                is_negated=False,
                is_openended=is_openended,
            )


@dataclasses.dataclass(frozen=True)
class SearchFilter:
    class FilterOperator(enum.Enum):
        # TODO: use iris from TROVE IriNamespace
        ANY_OF = 'any-of'
        NONE_OF = 'none-of'
        BEFORE = 'before'
        AFTER = 'after'

    filter_family: str
    property_path: tuple[str]
    value_set: frozenset[str]
    operator: FilterOperator

    @classmethod
    def from_filter_param(cls, param_name: JsonapiQueryparamName, param_value: str):
        try:  # "filter[<serialized_path>][<operator>]"
            (serialized_path, operator_value) = param_name.bracketed_names
            operator = SearchFilter.FilterOperator[operator_value]
        except ValueError:
            try:  # "filter[<serialized_path>]" (with default operator)
                (serialized_path,) = param_name.bracketed_names
                operator = SearchFilter.FilterOperator.ANY_OF
            except ValueError:
                raise exceptions.InvalidSearchParam(
                    f'expected 1 or 2 bracketed queryparam-name segments, '
                    f'got {len(param_name.bracketed_names)} (in "{param_name}")'
                )
        return cls(
            filter_family=param_name.family,
            property_path=tuple(split_queryparam_value(serialized_path)),
            value_set=frozenset(split_queryparam_value(param_value)),
            operator=operator,
        )


@dataclasses.dataclass(frozen=True)
class CardsearchParams:
    cardsearch_text: str
    cardsearch_textsegment_list: tuple[Textsegment]
    cardsearch_filter_set: frozenset[SearchFilter]
    include: typing.Optional[frozenset[tuple[str]]] = None
    sort: typing.Optional[str] = None
    index_strategy_name: typing.Optional[str] = None

    @classmethod
    def from_querystring(cls, querystring: str):
        _queryparams = queryparams_from_querystring(querystring)
        _cardsearch_text = ' '.join(
            param_value
            for _, param_value
            in _queryparams.get('cardSearchText', ())
        )
        return cls(
            cardsearch_text=_cardsearch_text,
            cardsearch_textsegment_list=frozenset(
                Textsegment.from_str(_cardsearch_text),
            ),
            cardsearch_filter_set=frozenset(
                SearchFilter.from_filter_param(param_name, param_value)
                for (param_name, param_value)
                in _queryparams.get('cardSearchFilter', ())
            ),
            index_strategy_name=_queryparams.get('indexStrategy'),
            # TODO: include, sort
        )


@dataclasses.dataclass(frozen=True)
class PropertysearchParams:
    propertysearch_textsegment_list: frozenset[str]
    propertysearch_filter_set: frozenset[SearchFilter]
    cardsearch_textsegment_list: frozenset[str]
    cardsearch_filter_set: frozenset[SearchFilter]


@dataclasses.dataclass(frozen=True)
class ValuesearchParams:
    valuesearch_textsegment_list: frozenset[str]
    valuesearch_filter_set: frozenset[SearchFilter]
    cardsearch_textsegment_list: frozenset[str]
    cardsearch_filter_set: frozenset[SearchFilter]
