import dataclasses
import enum
import itertools
import logging
import typing

from share.search import exceptions
from trove.util.queryparams import (
    JsonapiQueryparamDict,
    JsonapiQueryparamName,
    split_queryparam_value,
    queryparams_from_querystring,
)
from trove.vocab.osfmap import osfmap_labeler, is_date_property


logger = logging.getLogger(__name__)


###
# special characters in search text:
NEGATE_WORD_OR_PHRASE = '-'
DOUBLE_QUOTATION_MARK = '"'

DESCENDING_SORT_PREFIX = '-'


###
# dataclasses for parsed search-api query parameters

@dataclasses.dataclass(frozen=True)
class Textsegment:
    text: str
    is_fuzzy: bool = True
    is_negated: bool = False
    is_openended: bool = False
    # TODO: at_propertypath: Optional[tuple]

    def __post_init__(self):
        if self.is_negated and self.is_fuzzy:
            raise ValueError(f'{self}: cannot have both is_negated and is_fuzzy')

    def words(self):
        return self.text.split()

    @classmethod
    def split_str(cls, text: str) -> frozenset['Textsegment']:
        return frozenset(cls._split_str(text))

    @classmethod
    def _split_str(cls, text: str) -> typing.Iterable['Textsegment']:
        '''parse search text into words and quoted phrases
        '''
        _in_quotes = False
        _last_quote_prefix = None
        _text_remaining = text
        while _text_remaining:
            (  # split on the next "
                _text_chunk,
                _quote_mark,
                _text_remaining,
            ) = _text_remaining.partition(DOUBLE_QUOTATION_MARK)
            _text_chunk = _text_chunk.strip()
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
        _all_wordgroups = (
            (_each_word_negated, list(_words))
            for (_each_word_negated, _words) in itertools.groupby(
                text_chunk.split(),
                key=lambda word: word.startswith(NEGATE_WORD_OR_PHRASE),
            )
        )
        (*_wordgroups, (_lastgroup_negated, _lastgroup_words)) = _all_wordgroups
        for _each_word_negated, _words in _wordgroups:
            yield from cls._from_fuzzy_wordgroup(
                _each_word_negated,
                _words,
                is_openended=False,
            )
        yield from cls._from_fuzzy_wordgroup(
            _lastgroup_negated,
            _lastgroup_words,
            is_openended=is_openended,
        )

    @classmethod
    def _from_fuzzy_wordgroup(cls, each_word_negated: bool, words: typing.Iterable[str], *, is_openended=False):
        if each_word_negated:
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

        def is_date_operator(self):
            return self in (self.BEFORE, self.AFTER)

    property_path: tuple[str]
    value_set: frozenset[str]
    operator: FilterOperator

    @classmethod
    def for_queryparam_family(cls, queryparams: JsonapiQueryparamDict, queryparam_family: str):
        return frozenset(
            cls.from_filter_param(param_name, param_value)
            for (param_name, param_value)
            in queryparams.get(queryparam_family, ())
        )

    @classmethod
    def from_filter_param(cls, param_name: JsonapiQueryparamName, param_value: str):
        try:  # "filter[<serialized_path>][<operator>]"
            (_serialized_path, _operator_value) = param_name.bracketed_names
        except ValueError:
            try:  # "filter[<serialized_path>]" (with default operator)
                (_serialized_path,) = param_name.bracketed_names
            except ValueError:
                raise exceptions.InvalidSearchParam(
                    f'expected one or two bracketed queryparam-name segments'
                    f' ({len(param_name.bracketed_names)} in "{param_name}")'
                )
            else:  # default operator
                _operator = SearchFilter.FilterOperator.ANY_OF
        else:  # given operator
            try:
                _operator = SearchFilter.FilterOperator(_operator_value)
            except ValueError:
                raise ValueError(f'unrecognized search-filter operator "{_operator}"')
        _value_list = []
        for _value in split_queryparam_value(param_value):
            if _operator.is_date_operator():
                _value_list.append(_value)  # TODO: vali-date
            else:
                try:
                    _iri = osfmap_labeler.iri_for_label(_value)
                except KeyError:  # not a known shorthand
                    _value_list.append(_value)  # assume iri already
                else:
                    _value_list.append(_iri)
        return cls(
            property_path=tuple(
                osfmap_labeler.iri_for_label(_pathstep)
                for _pathstep in split_queryparam_value(_serialized_path)
            ),
            value_set=frozenset(_value_list),
            operator=_operator,
        )


@dataclasses.dataclass(frozen=True)
class SortParam:
    property_iri: str
    descending: bool = False

    @classmethod
    def from_sort_param(cls, param_value: str | None) -> tuple['SortParam']:
        if not param_value:
            return ()
        return tuple(cls._from_sort_param_str(param_value))

    @classmethod
    def _from_sort_param_str(cls, param_value: str) -> typing.Iterable['SortParam']:
        for _sort in split_queryparam_value(param_value):
            _sort_property = _sort.lstrip(DESCENDING_SORT_PREFIX)
            try:
                _property_iri = osfmap_labeler.iri_for_label(_sort_property)
            except KeyError:
                _property_iri = _sort_property
            if not is_date_property(_property_iri):
                raise ValueError(f'bad sort: {_sort_property}')  # TODO: nice response
            yield cls(
                property_iri=_property_iri,
                descending=param_value.startswith(DESCENDING_SORT_PREFIX),
            )


@dataclasses.dataclass(frozen=True)
class CardsearchParams:
    # TODO: total_filter_set (to limit "total counts" for e.g. type-specific search pages)
    cardsearch_text: str
    cardsearch_textsegment_set: frozenset[Textsegment]
    cardsearch_filter_set: frozenset[SearchFilter]
    include: frozenset[tuple[str]]
    sort: tuple[SortParam]
    index_strategy_name: str

    @classmethod
    def from_querystring(cls, querystring: str) -> 'CardsearchParams':  # TODO py3.11: typing.Self
        return cls.from_queryparams(queryparams_from_querystring(querystring))

    @staticmethod
    def from_queryparams(queryparams: JsonapiQueryparamDict) -> 'CardsearchParams':
        _cardsearch_text = _get_text_queryparam(queryparams, 'cardSearchText')
        return CardsearchParams(
            cardsearch_text=_cardsearch_text,
            cardsearch_textsegment_set=Textsegment.split_str(_cardsearch_text),
            cardsearch_filter_set=SearchFilter.for_queryparam_family(queryparams, 'cardSearchFilter'),
            index_strategy_name=_get_single_value(queryparams, 'indexStrategy'),
            sort=SortParam.from_sort_param(_get_single_value(queryparams, 'sort')),
            include=None,  # TODO
        )


@dataclasses.dataclass(frozen=True)
class PropertysearchParams(CardsearchParams):
    # includes fields from CardsearchParams, because a
    # propertysearch is run in context of a cardsearch
    propertysearch_text: str
    propertysearch_textsegment_set: frozenset[str]
    propertysearch_filter_set: frozenset[SearchFilter]

    # override CardsearchParams
    @staticmethod
    def from_queryparams(queryparams: JsonapiQueryparamDict) -> 'PropertysearchParams':
        _propertysearch_text = _get_text_queryparam(queryparams, 'propertySearchText')
        return PropertysearchParams(
            **dataclasses.asdict(
                CardsearchParams.from_queryparams(queryparams),
            ),
            propertysearch_text=_propertysearch_text,
            propertysearch_textsegment_set=Textsegment.split_str(_propertysearch_text),
            propertysearch_filter_set=SearchFilter.for_queryparam_family(queryparams, 'propertySearchFilter'),
        )


@dataclasses.dataclass(frozen=True)
class ValuesearchParams(CardsearchParams):
    # includes fields from CardsearchParams, because a
    # valuesearch is always in context of a cardsearch
    valuesearch_property_path: tuple[str]
    valuesearch_text: str
    valuesearch_textsegment_set: frozenset[str]
    valuesearch_filter_set: frozenset[SearchFilter]

    # override CardsearchParams
    @staticmethod
    def from_queryparams(queryparams: JsonapiQueryparamDict) -> 'ValuesearchParams':
        _valuesearch_text = _get_text_queryparam(queryparams, 'valueSearchText')
        _raw_property_path = _get_single_value(queryparams, 'valueSearchPropertyPath')
        if not _raw_property_path:
            raise ValueError('TODO: 400 valueSearchPropertyPath required')
        return ValuesearchParams(
            **dataclasses.asdict(CardsearchParams.from_queryparams(queryparams)),
            valuesearch_property_path=tuple(
                osfmap_labeler.iri_for_label(_pathstep)
                for _pathstep in split_queryparam_value(_raw_property_path)
            ),
            valuesearch_text=_valuesearch_text,
            valuesearch_textsegment_set=Textsegment.split_str(_valuesearch_text),
            valuesearch_filter_set=SearchFilter.for_queryparam_family(queryparams, 'valueSearchFilter'),
        )


###
# local helpers

def _get_text_queryparam(queryparams: JsonapiQueryparamDict, queryparam_family: str) -> str:
    '''concat all values for the given queryparam family into one str
    '''
    return ' '.join(
        param_value
        for _, param_value
        in queryparams.get(queryparam_family, ())
    )


def _get_single_value(queryparams: JsonapiQueryparamDict, queryparam_family: str):
    _paramlist = queryparams.get(queryparam_family)
    if not _paramlist:
        return None
    try:
        ((_, _paramvalue),) = _paramlist
    except ValueError:
        raise ValueError(f'expected at most one {queryparam_family} value, got {_paramlist}')
    else:
        return _paramvalue
