from __future__ import annotations
from collections.abc import (
    Generator,
    Mapping,
    Collection,
    Iterable,
)
import dataclasses
import enum
import functools
import logging
import types
import typing

from django.http import QueryDict

from trove import exceptions as trove_exceptions
from trove.trovesearch.page_cursor import (
    DEFAULT_PAGE_SIZE,
    PageCursor,
)
from trove.util.frozen import freeze
from trove.util.propertypath import (
    ONE_GLOB_PROPERTYPATH,
    PropertypathSet,
    Propertypath,
    is_globpath,
)
from trove.util.trove_params import BasicTroveParams
from trove.util.queryparams import (
    QueryparamDict,
    QueryparamName,
    split_queryparam_value,
    join_queryparam_value,
    get_single_value,
)
from trove.vocab import osfmap
from trove.vocab.jsonapi import JSONAPI_LINK
from trove.vocab.trove import trove_json_shorthand
from trove.vocab.namespaces import RDF, TROVE, OWL, FOAF, DCTERMS
if typing.TYPE_CHECKING:
    from primitive_metadata.primitive_rdf import IriShorthand


logger = logging.getLogger(__name__)


###
# constants for use in query param parsing

# special characters in "...SearchText" values
NEGATE_WORD_OR_PHRASE = '-'
DOUBLE_QUOTATION_MARK = '"'

# optional prefix for "sort" values
DESCENDING_SORT_PREFIX = '-'

DEFAULT_PROPERTYPATH_SET: PropertypathSet = frozenset([ONE_GLOB_PROPERTYPATH])

DEFAULT_INCLUDES_BY_TYPE: Mapping[str, frozenset[Propertypath]] = freeze({
    TROVE.Indexcard: set(),
    TROVE.Cardsearch: {
        (TROVE.searchResultPage,),
        (TROVE.relatedPropertyList,),
    },
    TROVE.Valuesearch: {
        (TROVE.searchResultPage,),
    },
    TROVE.SearchResult: {
        (TROVE.indexCard,),
    },
})

DEFAULT_FIELDS_BY_TYPE: Mapping[str, tuple[Propertypath, ...]] = freeze({
    TROVE.Indexcard: [
        (TROVE.resourceMetadata,),
        (TROVE.focusIdentifier,),
        (DCTERMS.issued,),
        (DCTERMS.modified,),
        (FOAF.primaryTopic),
    ],
    TROVE.Cardsearch: [
        (TROVE.totalResultCount,),
        (TROVE.cardSearchText,),
        (TROVE.cardSearchFilter,),
        (JSONAPI_LINK,),
    ],
    TROVE.Valuesearch: [
        (TROVE.propertyPath,),
        (TROVE.valueSearchText,),
        (TROVE.valueSearchFilter,),
        (TROVE.cardSearchText,),
        (TROVE.cardSearchFilter,),
    ],
})


class ValueType(enum.Enum):
    # note: enum values are iris
    IRI = TROVE['value-type/iri']
    DATE = TROVE['value-type/date']
    INTEGER = TROVE['value-type/integer']

    @classmethod
    def from_shortname(cls, shortname: str) -> typing.Self:
        _iri = trove_json_shorthand().expand_iri(shortname)
        return cls(_iri)

    @classmethod
    def shortnames(cls) -> Generator[str]:
        for _value_type in cls:
            yield _value_type.to_shortname()

    def to_shortname(self) -> str:
        return trove_json_shorthand().compact_iri(self.value)


###
# dataclasses for parsed search-api query parameters


@dataclasses.dataclass(frozen=True)
class TrovesearchParams(BasicTroveParams):
    static_focus_type: typing.ClassVar[str]  # expected on subclasses

    @classmethod
    def _default_shorthand(cls) -> IriShorthand:  # NOTE: osfmap special
        return osfmap.osfmap_json_shorthand()

    @classmethod
    def _default_include(cls) -> PropertypathSet:
        return DEFAULT_INCLUDES_BY_TYPE.get(cls.static_focus_type, frozenset())

    @classmethod
    def _default_attrpaths(cls) -> Mapping[str, tuple[Propertypath, ...]]:
        return DEFAULT_FIELDS_BY_TYPE


@dataclasses.dataclass(frozen=True)
class SearchText:
    text: str
    propertypath_set: PropertypathSet = DEFAULT_PROPERTYPATH_SET

    @classmethod
    def from_queryparam_family(cls, queryparams: QueryparamDict, queryparam_family: str) -> frozenset[typing.Self]:
        return frozenset(cls.iter_from_queryparam_family(queryparams, queryparam_family))

    @classmethod
    def iter_from_queryparam_family(cls, queryparams: QueryparamDict, queryparam_family: str) -> Generator[typing.Self]:
        for (_param_name, _param_value) in queryparams.get(queryparam_family, ()):
            if _param_value:
                _searchtext = cls.from_searchtext_param_or_none(_param_name, _param_value)
                if _searchtext is not None:
                    yield _searchtext

    @classmethod
    def from_searchtext_param_or_none(cls, param_name: QueryparamName, param_value: str) -> typing.Self | None:
        _propertypath_set = (
            frozenset(osfmap.parse_osfmap_propertypath_set(param_name.bracketed_names[0], allow_globs=True))
            if param_name.bracketed_names
            else None
        )
        if _propertypath_set:
            if any((is_globpath(_path) and len(_path) > 1) for _path in _propertypath_set):
                raise trove_exceptions.InvalidQueryParamName(
                    str(param_name),
                    'may not use glob-paths longer than "*" with search-text parameters',
                )
        _searchtext = cls(text=param_value)
        if _propertypath_set:
            _searchtext = dataclasses.replace(_searchtext, propertypath_set=_propertypath_set)
        return _searchtext

    @classmethod
    def queryparams_from_searchtext(
        self,
        queryparam_family: str,
        cardsearch_searchtext: Iterable[SearchText],
    ) -> Generator[tuple[str, str]]:
        for searchtext in cardsearch_searchtext:
            _qp_name = QueryparamName(
                queryparam_family,
                (osfmap.osfmap_propertypath_set_key(searchtext.propertypath_set),)
            )
            yield str(_qp_name), searchtext.text


@dataclasses.dataclass(frozen=True)
class SearchFilter:
    class FilterOperator(enum.Enum):
        # iri values
        ANY_OF = TROVE['any-of']
        NONE_OF = TROVE['none-of']
        IS_PRESENT = TROVE['is-present']
        IS_ABSENT = TROVE['is-absent']
        BEFORE = TROVE['before']
        AFTER = TROVE['after']
        AT_DATE = TROVE['at-date']

        @classmethod
        def from_shortname(cls, shortname: str) -> typing.Self:
            _iri = trove_json_shorthand().expand_iri(shortname)
            return cls(_iri)

        def to_shortname(self) -> str:
            return trove_json_shorthand().compact_iri(self.value)

        def is_date_operator(self) -> bool:
            return self in (self.BEFORE, self.AFTER, self.AT_DATE)

        def is_iri_operator(self) -> bool:
            return self in (self.ANY_OF, self.NONE_OF)

        def is_valueless_operator(self) -> bool:
            return self in (self.IS_PRESENT, self.IS_ABSENT)

    operator: FilterOperator
    value_set: frozenset[str]
    propertypath_set: PropertypathSet = DEFAULT_PROPERTYPATH_SET

    @classmethod
    def from_queryparam_family(cls, queryparams: QueryparamDict, queryparam_family: str) -> frozenset[typing.Self]:
        return frozenset(
            cls.from_filter_param(param_name, param_value)
            for (param_name, param_value)
            in queryparams.get(queryparam_family, ())
        )

    @classmethod
    def from_filter_param(cls, param_name: QueryparamName, param_value: str) -> typing.Self:
        _operator = None
        try:  # "filter[<serialized_path_set>][<operator>]"
            (_serialized_path_set, _operator_value) = param_name.bracketed_names
        except ValueError:
            try:  # "filter[<serialized_path_set>]" (with default operator)
                (_serialized_path_set,) = param_name.bracketed_names
            except ValueError:
                raise trove_exceptions.InvalidQueryParamName(
                    f'expected one or two bracketed queryparam-name segments'
                    f' ({len(param_name.bracketed_names)} in "{param_name}")'
                )
        else:  # given operator
            if _operator_value:
                try:
                    _operator = SearchFilter.FilterOperator.from_shortname(_operator_value)
                except ValueError:
                    raise trove_exceptions.InvalidQueryParamName(
                        str(param_name),
                        f'unknown filter operator "{_operator_value}"',
                    )
        _propertypath_set = frozenset(osfmap.parse_osfmap_propertypath_set(_serialized_path_set))
        _is_date_filter = all(
            osfmap.is_date_property(_path[-1])
            for _path in _propertypath_set
        )
        if _operator is None:  # default operator
            _operator = (
                SearchFilter.FilterOperator.AT_DATE
                if _is_date_filter
                else SearchFilter.FilterOperator.ANY_OF
            )
        if _operator.is_date_operator() and not _is_date_filter:
            raise trove_exceptions.InvalidQueryParamName(
                str(param_name),
                f'cannot use date operator "{_operator.to_shortname()}" on non-date property'
            )
        _value_list = []
        if not _operator.is_valueless_operator():
            for _value in split_queryparam_value(param_value):
                if _is_date_filter:
                    _value_list.append(_value)  # TODO: vali-date
                else:
                    _value_list.append(osfmap.osfmap_json_shorthand().expand_iri(_value))
        return cls(
            value_set=frozenset(_value_list),
            operator=_operator,
            propertypath_set=_propertypath_set,
        )

    def is_sameas_filter(self) -> bool:
        '''detect the special filter for matching exact identifier iris
        '''
        return (
            self.propertypath_set == {(OWL.sameAs,)}
            and self.operator == SearchFilter.FilterOperator.ANY_OF
        )

    def is_type_filter(self) -> bool:
        '''detect the special filter for matching resource type
        '''
        return (
            self.propertypath_set == {(RDF.type,)}
            and self.operator == SearchFilter.FilterOperator.ANY_OF
        )

    def as_queryparam(self, queryparam_family: str) -> tuple[str, str]:
        _qp_name = QueryparamName(queryparam_family, (
            osfmap.osfmap_propertypath_set_key(self.propertypath_set),
            self.operator.to_shortname(),
        ))
        _qp_value = join_queryparam_value(
            osfmap.osfmap_json_shorthand().compact_iri(_value)
            for _value in self.value_set
        )
        return str(_qp_name), _qp_value


@dataclasses.dataclass(frozen=True)
class SortParam:
    value_type: ValueType
    propertypath: Propertypath
    descending: bool

    @classmethod
    def from_sort_queryparams(cls, queryparams: QueryparamDict) -> tuple[SortParam, ...]:
        return tuple(filter(None, (
            cls._from_sort_queryparam(_param_name, _param_value)
            for (_param_name, _param_value)
            in queryparams.get('sort', ())
        )))

    @classmethod
    def _from_sort_queryparam(
        cls,
        param_name: QueryparamName,
        param_value: str,
    ) -> SortParam | None:
        if not param_value or param_value == '-relevance':
            return None
        _value_type = ValueType.DATE  # default
        if param_name.bracketed_names:
            try:  # "sort[<value_type>]"
                (_value_type_str,) = param_name.bracketed_names
                if _value_type_str:
                    _value_type = ValueType.from_shortname(_value_type_str)
                    if _value_type not in (ValueType.DATE, ValueType.INTEGER):
                        raise ValueError
            except ValueError:
                raise trove_exceptions.InvalidQueryParamName(str(param_name), (
                    'valid sort param names: sort,'
                    f' sort[{ValueType.DATE.to_shortname()}],'
                    f' sort[{ValueType.INTEGER.to_shortname()}],'
                ))
        _descending = param_value.startswith(DESCENDING_SORT_PREFIX)
        _rawpath = param_value.lstrip(DESCENDING_SORT_PREFIX)
        _path = osfmap.parse_osfmap_propertypath(_rawpath)
        return cls(
            value_type=_value_type,
            propertypath=_path,
            descending=_descending,
        )

    def __post_init__(self) -> None:
        if (
            self.value_type == ValueType.DATE
            and not is_date_path(self.propertypath)
        ):
            raise trove_exceptions.InvalidSort(
                '='.join(self.as_queryparam()),
                'may not sort by date on a path leading to a non-date property',
            )

    def as_queryparam(self) -> tuple[str, str]:
        _name = (
            'sort'
            if (self.value_type == ValueType.DATE)
            else f'sort[{self.value_type.to_shortname()}]'
        )
        _pathkey = osfmap.osfmap_propertypath_key(self.propertypath)
        _value = (f'-{_pathkey}' if self.descending else _pathkey)
        return (_name, _value)


@dataclasses.dataclass(frozen=True)
class IndexcardParams(TrovesearchParams):
    static_focus_type = TROVE.Indexcard


@dataclasses.dataclass(frozen=True)
class CardsearchParams(TrovesearchParams):
    cardsearch_searchtext: frozenset[SearchText]
    cardsearch_filter_set: frozenset[SearchFilter]
    index_strategy_name: str | None
    sort_list: tuple[SortParam, ...]
    page_cursor: PageCursor

    static_focus_type = TROVE.Cardsearch

    @classmethod
    def parse_queryparams(cls, queryparams: QueryparamDict) -> dict[str, typing.Any]:
        _filter_set = SearchFilter.from_queryparam_family(queryparams, 'cardSearchFilter')
        return {
            **super().parse_queryparams(queryparams),
            'cardsearch_searchtext': SearchText.from_queryparam_family(queryparams, 'cardSearchText'),
            'cardsearch_filter_set': _filter_set,
            'index_strategy_name': get_single_value(queryparams, 'indexStrategy'),
            'sort_list': SortParam.from_sort_queryparams(queryparams),
            'page_cursor': _get_page_cursor(queryparams),
        }

    @functools.cached_property
    def related_property_paths(self) -> tuple[Propertypath, ...]:
        return (
            _get_related_property_paths(self.cardsearch_filter_set)
            if (TROVE.relatedPropertyList,) in self.included_relations
            else ()
        )

    def cardsearch_type_iris(self) -> Generator[str]:
        for _filter in self.cardsearch_filter_set:
            if _filter.is_type_filter():
                yield from _filter.value_set

    @functools.cached_property
    def cardsearch_text_paths(self) -> PropertypathSet:
        return frozenset().union(*(
            searchtext.propertypath_set
            for searchtext in self.cardsearch_searchtext
        ))

    @functools.cached_property
    def cardsearch_text_glob_depths(self) -> frozenset[int]:
        return frozenset(
            len(_path)
            for _path in self.cardsearch_text_paths
            if is_globpath(_path)
        )

    def to_querydict(self) -> QueryDict:
        _querydict = super().to_querydict()
        for _qp_name, _qp_value in SearchText.queryparams_from_searchtext('cardSearchText', self.cardsearch_searchtext):
            _querydict[_qp_name] = _qp_value
        for _sort in self.sort_list:
            _qp_name, _qp_value = _sort.as_queryparam()
            _querydict.appendlist(_qp_name, _qp_value)
        if not self.page_cursor.is_basic():
            _querydict['page[cursor]'] = self.page_cursor.as_queryparam_value()
        elif self.page_cursor.page_size != DEFAULT_PAGE_SIZE:
            _querydict['page[size]'] = str(self.page_cursor.page_size)
        for _filter in self.cardsearch_filter_set:
            _qp_name, _qp_value = _filter.as_queryparam('cardSearchFilter')
            _querydict.appendlist(_qp_name, _qp_value)
        if self.index_strategy_name:
            _querydict['indexStrategy'] = self.index_strategy_name
        return _querydict


@dataclasses.dataclass(frozen=True)
class ValuesearchParams(CardsearchParams):
    # includes fields from CardsearchParams, because a
    # valuesearch is always in context of a cardsearch
    valuesearch_propertypath: Propertypath
    valuesearch_searchtext: frozenset[SearchText]
    valuesearch_filter_set: frozenset[SearchFilter]

    static_focus_type = TROVE.Valuesearch

    # override CardsearchParams
    @classmethod
    def parse_queryparams(cls, queryparams: QueryparamDict) -> dict:
        _raw_propertypath = get_single_value(queryparams, 'valueSearchPropertyPath')
        if not _raw_propertypath:
            raise trove_exceptions.MissingRequiredQueryParam('valueSearchPropertyPath')
        return {
            **super().parse_queryparams(queryparams),
            'valuesearch_propertypath': osfmap.parse_osfmap_propertypath(_raw_propertypath),
            'valuesearch_searchtext': SearchText.from_queryparam_family(queryparams, 'valueSearchText'),
            'valuesearch_filter_set': SearchFilter.from_queryparam_family(queryparams, 'valueSearchFilter'),
        }

    def __post_init__(self) -> None:
        if osfmap.is_date_property(self.valuesearch_propertypath[-1]):
            # date-value limitations
            if self.valuesearch_searchtext:
                raise trove_exceptions.InvalidQueryParams(
                    'valueSearchText may not be used with valueSearchPropertyPath leading to a "date" property',
                )
            if self.valuesearch_filter_set:
                raise trove_exceptions.InvalidQueryParams(
                    'valueSearchFilter may not be used with valueSearchPropertyPath leading to a "date" property',
                )

    def to_querydict(self) -> QueryDict:
        _querydict = super().to_querydict()
        _querydict['valueSearchPropertyPath'] = osfmap.osfmap_propertypath_key(self.valuesearch_propertypath)
        for _qp_name, _qp_value in SearchText.queryparams_from_searchtext('valueSearchText', self.valuesearch_searchtext):
            _querydict[_qp_name] = _qp_value
        for _filter in self.valuesearch_filter_set:
            _qp_name, _qp_value = _filter.as_queryparam('valueSearchFilter')
            _querydict.appendlist(_qp_name, _qp_value)
        return _querydict

    def valuesearch_iris(self) -> Generator[str]:
        for _filter in self.valuesearch_filter_set:
            if _filter.is_sameas_filter():
                yield from _filter.value_set

    def valuesearch_type_iris(self) -> Generator[str]:
        for _filter in self.valuesearch_filter_set:
            if _filter.is_type_filter():
                yield from _filter.value_set


###
# helper functions

def is_date_path(path: Propertypath) -> bool:
    return bool(path) and osfmap.is_date_property(path[-1])


def _get_text_queryparam(queryparams: QueryparamDict, queryparam_family: str) -> str:
    '''concat all values for the given queryparam family into one str
    '''
    return ' '.join(
        param_value
        for _, param_value
        in queryparams.get(queryparam_family, ())
    )


def _get_related_property_paths(filter_set: Collection[SearchFilter]) -> tuple[Propertypath, ...]:
    # hard-coded for osf.io search pages, static list per type
    # TODO: replace with some dynamism, maybe a 'significant_terms' aggregation
    _type_iris: set[str] = set()
    for _filter in filter_set:
        if _filter.is_type_filter():
            _type_iris.update(_filter.value_set)
    return osfmap.suggested_property_paths(_type_iris)


def _get_page_cursor(queryparams: QueryparamDict) -> PageCursor:
    _cursor_value = get_single_value(queryparams, QueryparamName('page', ('cursor',)))
    if _cursor_value:
        return PageCursor.from_queryparam_value(_cursor_value)
    _size_value = get_single_value(queryparams, QueryparamName('page', ('size',)))
    if _size_value is None:
        return PageCursor()
    try:
        _size = int(_size_value)
    except ValueError:
        raise trove_exceptions.InvalidQueryParamValue('page[size]')
    return PageCursor(page_size=_size)


def _frozen_mapping(**kwargs: dict[str, typing.Any]) -> Mapping[str, typing.Any]:
    return types.MappingProxyType(kwargs)
