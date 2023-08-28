import dataclasses
import enum
import itertools
import logging
import typing

from django.http import QueryDict

from share.search import exceptions
from trove.util.queryparams import (
    QueryparamDict,
    QueryparamName,
    split_queryparam_value,
    queryparams_from_querystring,
    QUERYPARAM_VALUES_DELIM,
)
from trove.vocab.osfmap import (
    osfmap_labeler,
    is_date_property,
    suggested_property_paths,
    OSFMAP_VOCAB,
)
from trove.vocab.namespaces import RDF


logger = logging.getLogger(__name__)


###
# special characters in search text:
NEGATE_WORD_OR_PHRASE = '-'
DOUBLE_QUOTATION_MARK = '"'

DESCENDING_SORT_PREFIX = '-'

DEFAULT_PAGE_SIZE = 13


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
        if text_chunk == '*':
            return  # special case for COS employees used to the old search page
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
                _word_without_prefix = _word[len(NEGATE_WORD_OR_PHRASE):]
                if _word_without_prefix:
                    yield cls(
                        text=_word_without_prefix,
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
        IS_PRESENT = 'is-present'
        IS_ABSENT = 'is-absent'
        BEFORE = 'before'
        AFTER = 'after'
        AT_DATE = 'at-date'

        def is_date_operator(self):
            return self in (self.BEFORE, self.AFTER, self.AT_DATE)

        def is_iri_operator(self):
            return self in (self.ANY_OF, self.NONE_OF)

        def is_valueless_operator(self):
            return self in (self.IS_PRESENT, self.IS_ABSENT)

    property_path: tuple[str]
    value_set: frozenset[str]
    operator: FilterOperator
    original_param_name: typing.Optional[str] = None
    original_param_value: typing.Optional[str] = None

    @classmethod
    def for_queryparam_family(cls, queryparams: QueryparamDict, queryparam_family: str):
        return frozenset(
            cls.from_filter_param(param_name, param_value)
            for (param_name, param_value)
            in queryparams.get(queryparam_family, ())
        )

    @classmethod
    def from_filter_param(cls, param_name: QueryparamName, param_value: str):
        _operator = None
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
        else:  # given operator
            if _operator_value:
                try:
                    _operator = SearchFilter.FilterOperator(_operator_value)
                except ValueError:
                    raise ValueError(f'unrecognized search-filter operator "{_operator_value}"')
        _propertypath = tuple(
            osfmap_labeler.iri_for_label(_pathstep, default=_pathstep)
            for _pathstep in split_queryparam_value(_serialized_path)
        )
        _is_date_property = is_date_property(_propertypath[-1])
        if _operator is None:  # default operator
            _operator = (
                SearchFilter.FilterOperator.AT_DATE
                if _is_date_property
                else SearchFilter.FilterOperator.ANY_OF
            )
        if _operator.is_date_operator() and not _is_date_property:
            raise ValueError(f'cannot use date operator {_operator.value} on non-date property')
        _value_list = []
        if not _operator.is_valueless_operator():
            for _value in split_queryparam_value(param_value):
                if _is_date_property:
                    _value_list.append(_value)  # TODO: vali-date
                else:
                    try:
                        _iri = osfmap_labeler.iri_for_label(_value)
                    except KeyError:  # not a known shorthand
                        _value_list.append(_value)  # assume iri already
                    else:
                        _value_list.append(_iri)
        return cls(
            property_path=_propertypath,
            value_set=frozenset(_value_list),
            operator=_operator,
            original_param_name=str(param_name),
            original_param_value=param_value,
        )


@dataclasses.dataclass(frozen=True)
class SortParam:
    property_iri: str
    original_param_value: str
    descending: bool = False

    @classmethod
    def from_queryparams(cls, queryparams: QueryparamDict) -> tuple['SortParam']:
        _paramvalue = _get_single_value(queryparams, QueryparamName('sort'))
        if not _paramvalue or _paramvalue == '-relevance':
            return ()
        return tuple(cls._from_sort_param_str(_paramvalue))

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
                original_param_value=param_value,
            )


@dataclasses.dataclass(frozen=True)
class PageParam:
    cursor: str | None  # intentionally opaque; for IndexStrategy to generate/interpret
    size: int | None = None  # size is None iff cursor is not None

    @classmethod
    def from_queryparams(cls, queryparams: QueryparamDict) -> 'PageParam':
        _cursor = _get_single_value(queryparams, QueryparamName('page', ['cursor']))
        if _cursor:
            return cls(cursor=_cursor)
        _size = int(  # TODO: 400 response on non-int value
            _get_single_value(queryparams, QueryparamName('page', ['size']))
            or DEFAULT_PAGE_SIZE
        )
        return cls(size=_size, cursor=None)


@dataclasses.dataclass(frozen=True)
class CardsearchParams:
    cardsearch_text: str
    cardsearch_textsegment_set: frozenset[Textsegment]
    cardsearch_filter_set: frozenset[SearchFilter]
    index_strategy_name: str | None
    sort_list: tuple[SortParam]
    page: PageParam
    include: frozenset[tuple[str, ...]]
    related_property_paths: tuple[tuple[str, ...]]
    unnamed_iri_values: frozenset[str]

    @classmethod
    def from_querystring(cls, querystring: str) -> 'CardsearchParams':  # TODO py3.11: typing.Self
        return cls.from_queryparams(queryparams_from_querystring(querystring))

    @staticmethod
    def from_queryparams(queryparams: QueryparamDict) -> 'CardsearchParams':
        return CardsearchParams(**CardsearchParams.parse_cardsearch_queryparams(queryparams))

    @staticmethod
    def parse_cardsearch_queryparams(queryparams: QueryparamDict) -> dict:
        _cardsearch_text = _get_text_queryparam(queryparams, 'cardSearchText')
        _filter_set = SearchFilter.for_queryparam_family(queryparams, 'cardSearchFilter')
        return {
            'cardsearch_text': _cardsearch_text,
            'cardsearch_textsegment_set': Textsegment.split_str(_cardsearch_text),
            'cardsearch_filter_set': _filter_set,
            'index_strategy_name': _get_single_value(queryparams, QueryparamName('indexStrategy')),
            'sort_list': SortParam.from_queryparams(queryparams),
            'page': PageParam.from_queryparams(queryparams),
            'include': None,  # TODO
            'related_property_paths': _get_related_property_paths(_filter_set),
            'unnamed_iri_values': frozenset(),  # TODO: frozenset(_get_unnamed_iri_values(_filter_set)),
        }

    def to_querystring(self) -> str:
        return self.to_querydict().urlencode()

    def to_querydict(self) -> QueryDict:
        _querydict = QueryDict(mutable=True)
        if self.cardsearch_text:
            _querydict['cardSearchText'] = self.cardsearch_text
        if self.sort_list:
            _querydict['sort'] = QUERYPARAM_VALUES_DELIM.join(
                _sort.original_param_value
                for _sort in self.sort_list
            )
        if self.page.cursor:
            _querydict['page[cursor]'] = self.page.cursor
        elif self.page.size != DEFAULT_PAGE_SIZE:
            _querydict['page[size]'] = self.page.size
        for _filter in self.cardsearch_filter_set:
            _querydict.appendlist(_filter.original_param_name, _filter.original_param_value),
        if self.index_strategy_name:
            _querydict['indexStrategy'] = self.index_strategy_name
        # TODO: include 'include'
        return _querydict


@dataclasses.dataclass(frozen=True)
class ValuesearchParams(CardsearchParams):
    # includes fields from CardsearchParams, because a
    # valuesearch is always in context of a cardsearch
    valuesearch_property_path: tuple[str]
    valuesearch_text: str
    valuesearch_textsegment_set: frozenset[str]
    valuesearch_filter_set: frozenset[SearchFilter]
    original_valuesearch_property_path: str

    # override CardsearchParams
    @staticmethod
    def from_queryparams(queryparams: QueryparamDict) -> 'ValuesearchParams':
        _valuesearch_text = _get_text_queryparam(queryparams, 'valueSearchText')
        _raw_property_path = _get_single_value(queryparams, QueryparamName('valueSearchPropertyPath'))
        if not _raw_property_path:
            raise ValueError('TODO: 400 valueSearchPropertyPath required')
        return ValuesearchParams(
            **CardsearchParams.parse_cardsearch_queryparams(queryparams),
            valuesearch_property_path=tuple(
                osfmap_labeler.iri_for_label(_pathstep)
                for _pathstep in split_queryparam_value(_raw_property_path)
            ),
            valuesearch_text=_valuesearch_text,
            valuesearch_textsegment_set=Textsegment.split_str(_valuesearch_text),
            valuesearch_filter_set=SearchFilter.for_queryparam_family(queryparams, 'valueSearchFilter'),
            original_valuesearch_property_path=_raw_property_path,
        )

    def to_querydict(self):
        _querydict = super().to_querydict()
        _querydict['valueSearchPropertyPath'] = self.original_valuesearch_property_path
        if self.valuesearch_text:
            _querydict['valueSearchText'] = self.valuesearch_text
        for _filter in self.valuesearch_filter_set:
            _querydict.appendlist(_filter.original_param_name, _filter.original_param_value),
        return _querydict


###
# local helpers

def _get_text_queryparam(queryparams: QueryparamDict, queryparam_family: str) -> str:
    '''concat all values for the given queryparam family into one str
    '''
    return ' '.join(
        param_value
        for _, param_value
        in queryparams.get(queryparam_family, ())
    )


def _get_single_value(
    queryparams: QueryparamDict,
    queryparam_name: QueryparamName,
):
    _family_params = queryparams.get(queryparam_name.family, ())
    _paramvalues = [
        _paramvalue
        for _paramname, _paramvalue in _family_params
        if _paramname.bracketed_names == queryparam_name.bracketed_names
    ]
    if not _paramvalues:
        return None
    try:
        (_singlevalue,) = _paramvalues
    except ValueError:
        raise ValueError(f'expected at most one {queryparam_name} value, got {len(_paramvalues)}')
    else:
        return _singlevalue


def _get_related_property_paths(filter_set) -> tuple[tuple[str]]:
    # hard-coded for osf.io search pages, static list per type
    # TODO: replace with some dynamism, maybe a 'significant_terms' aggregation
    _type_iris = set()
    for _filter in filter_set:
        if _filter.property_path == (RDF.type,):
            if _filter.operator == SearchFilter.FilterOperator.ANY_OF:
                _type_iris.update(_filter.value_set)
            if _filter.operator == SearchFilter.FilterOperator.NONE_OF:
                _type_iris.difference_update(_filter.value_set)
    return suggested_property_paths(_type_iris)


def _get_unnamed_iri_values(filter_set) -> typing.Iterable[str]:
    for _filter in filter_set:
        if _filter.operator.is_iri_operator():
            for _iri in _filter.value_set:
                if _iri not in OSFMAP_VOCAB:
                    yield _iri
