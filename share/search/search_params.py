import dataclasses
import enum
import itertools
import re
import typing

from django import http

from share.search import exceptions


# two special characters in search text:
NEGATE_WORD_OR_PHRASE = '-'
PHRASE_QUOTATION_MARK = '"'

# jsonapi query-param parsing
QUERYPARAM_FAMILY_REGEX = re.compile(r'^[a-zA-Z0-9][-_a-zA-Z0-9]*(?=\[|$)')
QUERYPARAM_MEMBER_REGEX = re.compile(r'\[(?P<member_name>[a-zA-Z0-9][-_a-zA-Z0-9]*)?\]')
QUERYPARAM_VALUES_DELIM = ','


class FilterOperator(enum.Enum):
    ANY_OF = 'any-of'
    NONE_OF = 'none-of'
    BEFORE = 'before'
    AFTER = 'after'


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
            bracketed_match = QUERYPARAM_MEMBER_REGEX.match(queryparam_name, next_position)
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


@dataclasses.dataclass(frozen=True)
class SearchTextSegment:
    text: str
    is_fuzzy: bool
    is_negated: bool
    is_openended: bool

    def __post_init__(self):
        if self.is_negated and self.is_openended:
            raise ValueError(f'{self}: cannot have both is_negated and is_openended')
        if self.is_negated and self.is_fuzzy:
            raise ValueError(f'{self}: cannot have both is_negated and is_fuzzy')

    @classmethod
    def from_text(cls, search_text: str) -> typing.Iterable['SearchTextSegment']:
        '''parse search text into words and quoted phrases
        '''
        in_quotes = False
        phrase_prefix = None
        remaining = search_text
        while remaining:
            text_chunk, quote_mark, remaining = remaining.partition(PHRASE_QUOTATION_MARK)
            if text_chunk.strip():
                is_negated = (phrase_prefix == NEGATE_WORD_OR_PHRASE)
                is_openended = (
                    not is_negated
                    and not quote_mark
                    and not remaining
                )
                if in_quotes:
                    yield cls(
                        text=text_chunk,
                        is_fuzzy=False,
                        is_negated=is_negated,
                        is_openended=is_openended,
                    )
                else:  # not in_quotes
                    words = cls.split_into_words(
                        text_chunk,
                        is_openended=is_openended,
                    )
                    yield from words
                    # additional fuzzy-phrase segments, because written order might help
                    for is_negated, fuzzy_phrase in itertools.groupby(
                        words,
                        key=lambda word: word.is_negated,
                    ):
                        if not is_negated and len(fuzzy_phrase) > 1:
                            yield cls(
                                text=' '.join(fuzzy_phrase),
                                is_fuzzy=True,
                                is_negated=False,
                                is_openended=is_openended,
                            )
            if quote_mark:
                if in_quotes:  # end quote
                    in_quotes = False
                    phrase_prefix = None
                else:  # begin quote
                    in_quotes = True
                    phrase_prefix = text_chunk[-1:]

    @classmethod
    def split_into_words(cls, text: str, *, is_openended: bool) -> typing.Iterable['SearchTextSegment']:
        try:
            (*words, last_word) = text.split()
        except ValueError:
            pass  # no words
        else:
            for word in words:
                yield cls.from_word(word, is_openended=False)
            yield cls.from_word(last_word, is_openended=is_openended)

    @classmethod
    def from_word(cls, word: str, *, is_openended: bool) -> 'SearchTextSegment':
        if word.startswith(NEGATE_WORD_OR_PHRASE):
            is_negated = True
            word = word[len(NEGATE_WORD_OR_PHRASE):]  # remove prefix
        else:
            is_negated = False
        return cls(
            text=word,
            is_fuzzy=(not is_negated),
            is_negated=is_negated,
            is_openended=is_openended,
        )


@dataclasses.dataclass(frozen=True)
class SearchFilter:
    filter_family: str
    property_path: tuple[str]
    value_set: frozenset[str]
    operator: str

    @classmethod
    def from_filter_param(cls, param_name: JsonapiQueryparamName, param_value: str):
        try:  # "filter[<serialized_path>][<operator>]"
            (serialized_path, operator_value) = param_name.bracketed_names
        except ValueError:
            try:  # "filter[<serialized_path>]" (with default operator)
                (serialized_path,) = param_name.bracketed_names
                operator = FilterOperator.ANY_OF.value
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
class IndexCardSearchParams:
    card_search_text_set: frozenset[SearchTextSegment]
    card_search_filter_set: frozenset[SearchFilter]
    include: typing.Optional[frozenset[tuple[str]]] = None
    sort: typing.Optional[str] = None

    @classmethod
    def from_request(cls, request: http.HttpRequest):
        queryparams_by_family = _jsonapi_queryparams(request)
        return cls(
            card_search_text_set=frozenset(itertools.chain(*(
                SearchTextSegment.from_text(param_value)
                for _, param_value
                in queryparams_by_family.get('cardSearchText', ())
            ))),
            card_search_filter_set=frozenset(
                SearchFilter.from_filter_param(param_name, param_value)
                for (param_name, param_value)
                in queryparams_by_family.get('cardSearchFilter', ())
            ),
            # TODO: include, sort
        )


@dataclasses.dataclass(frozen=True)
class IndexPropertySearchParams:
    property_search_text_set: frozenset[str]
    property_search_filter_set: frozenset[SearchFilter]
    card_search_text_set: frozenset[str]
    card_search_filter_set: frozenset[SearchFilter]


@dataclasses.dataclass(frozen=True)
class IndexValueSearchParams:
    value_search_text_set: frozenset[str]
    value_search_filter_set: frozenset[SearchFilter]
    card_search_text_set: frozenset[str]
    card_search_filter_set: frozenset[SearchFilter]


def _jsonapi_queryparams(request: http.HttpRequest) -> dict[
        str,  # keyed by queryparam family
        list[tuple[JsonapiQueryparamName, str]],
]:
    by_family = {}
    for querydict in (request.GET, request.POST):
        if not querydict:
            continue
        for unparsed_param_name, param_value_list in querydict.lists():
            parsed_param_name = JsonapiQueryparamName.from_str(unparsed_param_name)
            for param_value in param_value_list:
                (
                    by_family
                    .setdefault(parsed_param_name.family, [])
                    .append((parsed_param_name, param_value))
                )
    return by_family
