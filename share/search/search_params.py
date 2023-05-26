import dataclasses
import enum
import itertools
import re
import typing
import urllib

from django.http import QueryDict

from share.search import exceptions


###
# special characters in search text:
NEGATE_WORD_OR_PHRASE = '-'
DOUBLE_QUOTATION_MARK = '"'


###
# jsonapi query parameter parsing:
# https://jsonapi.org/format/#query-parameters
QUERYPARAM_FAMILY_REGEX = re.compile(
    r'^[a-zA-Z0-9]'     # initial alphanumeric,
    r'[-_a-zA-Z0-9]*'   # - and _ ok from then,
    r'(?=\[|$)'         # followed by [ or end.
)
QUERYPARAM_FAMILYMEMBER_REGEX = re.compile(
    r'\['                   # open square-bracket,
    r'(?P<member_name>'     # 'member_name' group,
    r'[a-zA-Z0-9]'          # starts alphanumeric,
    r'[-_a-zA-Z0-9]*'       # allow - or _ within,
    r')?'                   # empty brackets fine,
    r'\]'                   # need an end bracket.
)
# is common (but not required) for a query parameter
# value to be split (on comma) into a list of values
QUERYPARAM_VALUES_DELIM = ','


@dataclasses.dataclass(frozen=True)
class JsonapiQueryparamName:
    family: str
    bracketed_names: tuple[str]

    @classmethod
    def from_str(cls, queryparam_name: str) -> 'JsonapiQueryparamName':
        family_match = QUERYPARAM_FAMILY_REGEX.match(queryparam_name)
        if not family_match:
            raise ValueError(f'invalid queryparam name "{queryparam_name}"')
        family = family_match.group()
        next_position = family_match.end()
        bracketed_names = []
        while next_position < len(queryparam_name):
            bracketed_match = QUERYPARAM_FAMILYMEMBER_REGEX.match(queryparam_name, next_position)
            if not bracketed_match:
                raise ValueError(f'invalid queryparam name "{queryparam_name}"')
            bracketed_names.append(bracketed_match.group('member_name'))
            next_position = bracketed_match.end()
        if next_position != len(queryparam_name):
            raise ValueError(f'invalid queryparam name "{queryparam_name}"')
        return cls(family, tuple(bracketed_names))

    def __str__(self):
        return ''.join((
            self.family,
            *(
                f'[{bracketed_name}]'
                for bracketed_name in self.bracketed_names
            ),
        ))


JsonapiQueryParams = dict[
    str,  # keyed by queryparam family
    list[tuple[JsonapiQueryparamName, str]],
]


def queryparams_from_iri(iri: str) -> JsonapiQueryParams:
    _parsed_iri = urllib.parse.urlparse(iri)
    return queryparams_from_querydict(QueryDict(_parsed_iri.query))


def queryparams_from_querydict(querydict: QueryDict) -> JsonapiQueryParams:
    _queryparams: JsonapiQueryParams = {}
    for _unparsed_name, _param_value_list in querydict.lists():
        _parsed_name = JsonapiQueryparamName.from_str(_unparsed_name)
        for param_value in _param_value_list:
            (
                _queryparams
                .setdefault(_parsed_name.family, [])
                .append((_parsed_name, param_value))
            )
    return _queryparams


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

    def wordset(self) -> typing.Iterable[tuple[bool, typing.Iterable['Textsegment']]]:
        try:
            (*words, lastword) = self.text.split()
        except ValueError:
            pass  # no words
        else:
            for word in words:
                yield Textsegment.from_word(
                    word,
                    is_openended=False,
                    is_fuzzy=self.is_fuzzy,
                )
            if words:
                yield Textsegment.from_word(
                    lastword,
                    is_openended=self.is_openended,
                    is_fuzzy=self.is_fuzzy,
                )

    @classmethod
    def from_str(cls, text: str) -> typing.Iterable['Textsegment']:
        '''parse search text into words and quoted phrases
        '''
        in_quotes = False
        last_quote_prefix = None
        text_remaining = text
        while text_remaining:
            text_chunk, quote_mark, text_remaining = text_remaining.partition(DOUBLE_QUOTATION_MARK)
            is_openended = (
                not quote_mark
                and not text_remaining
            )
            if in_quotes:
                yield cls(
                    text=text_chunk,
                    is_fuzzy=False,
                    is_negated=(last_quote_prefix == NEGATE_WORD_OR_PHRASE),
                    is_openended=is_openended,
                )
            else:
                yield from cls._from_fuzzy_text(
                    text_chunk,
                    is_openended=is_openended,
                )
            if quote_mark:
                if in_quotes:  # end quote
                    in_quotes = False
                    last_quote_prefix = None
                else:  # begin quote
                    in_quotes = True
                    last_quote_prefix = text_chunk[-1:]

    @classmethod
    def _from_fuzzy_text(cls, text_chunk: str, is_openended: bool):
        (*wordgroups, lastgroup) = itertools.groupby(
            text_chunk.split(),
            key=lambda word: word.startswith(NEGATE_WORD_OR_PHRASE),
        )
        for word_negated, words in wordgroups:
            yield from cls._from_fuzzy_wordgroup(word_negated, words)
        yield from cls._from_fuzzy_wordgroup(*lastgroup, is_openended=True)

    @classmethod
    def _from_fuzzy_wordgroup(cls, word_negated: bool, words: typing.Iterable[str], *, is_openended=False):
        if word_negated:
            for word in words:
                yield cls(
                    text=word[len(NEGATE_WORD_OR_PHRASE):],  # remove prefix
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

    @classmethod
    def from_word(cls, word: str, *, is_openended: bool, is_fuzzy: bool) -> 'Textsegment':
        if is_fuzzy and word.startswith(NEGATE_WORD_OR_PHRASE):
            is_negated = True
            word = word[len(NEGATE_WORD_OR_PHRASE):]  # remove prefix
        else:
            is_negated = False
        return cls(
            text=word,
            is_fuzzy=(is_fuzzy and not is_negated),
            is_negated=is_negated,
            is_openended=(is_openended and not is_negated),
        )


@dataclasses.dataclass(frozen=True)
class SearchFilter:
    class FilterOperator(enum.Enum):
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
            property_path=tuple(serialized_path.split(QUERYPARAM_VALUES_DELIM)),
            value_set=frozenset(param_value.split(QUERYPARAM_VALUES_DELIM)),
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
    def from_iri(cls, iri: str):
        _queryparams = queryparams_from_iri(iri)
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
