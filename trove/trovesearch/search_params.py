import collections
import dataclasses
import enum
import itertools
import logging
import typing
import urllib

from django.http import QueryDict
from primitive_metadata import primitive_rdf

from trove import exceptions as trove_exceptions
from trove.util.queryparams import (
    QueryparamDict,
    QueryparamName,
    split_queryparam_value,
    join_queryparam_value,
    queryparams_from_querystring,
)
from trove.vocab.osfmap import (
    osfmap_shorthand,
    is_date_property,
    suggested_property_paths,
    OSFMAP_THESAURUS,
)
from trove.vocab.trove import trove_shorthand
from trove.vocab.namespaces import RDF, TROVE, OWL, NAMESPACES_SHORTHAND


logger = logging.getLogger(__name__)


###
# constants for use in query param parsing

# special characters in "...SearchText" values
NEGATE_WORD_OR_PHRASE = '-'
DOUBLE_QUOTATION_MARK = '"'

# optional prefix for "sort" values
DESCENDING_SORT_PREFIX = '-'

# for "page[size]" values
DEFAULT_PAGE_SIZE = 13
MAX_PAGE_SIZE = 101

# between each step in a property path "foo.bar.baz"
PROPERTYPATH_DELIMITER = '.'

# special path-step that matches any property
GLOB_PATHSTEP = '*'
ONE_GLOB_PROPERTYPATH = (GLOB_PATHSTEP,)
DEFAULT_PROPERTYPATH_SET = frozenset([ONE_GLOB_PROPERTYPATH])


###
# dataclasses for parsed search-api query parameters


@dataclasses.dataclass(frozen=True)
class BaseTroveParams:
    iri_shorthand: primitive_rdf.IriShorthand = dataclasses.field(repr=False)
    include: frozenset[tuple[str, ...]]
    accept_mediatype: str | None

    @classmethod
    def from_querystring(cls, querystring: str) -> 'BaseTroveParams':  # TODO py3.11: typing.Self
        return cls.from_queryparams(queryparams_from_querystring(querystring))

    @classmethod
    def from_queryparams(cls, queryparams: QueryparamDict) -> 'BaseTroveParams':
        return cls(**cls.parse_queryparams(queryparams))

    @classmethod
    def parse_queryparams(cls, queryparams: QueryparamDict) -> dict:
        # subclasses should override and add their fields to super().parse_queryparams(queryparams)
        return {
            'iri_shorthand': cls._gather_shorthand(queryparams),
            'include': cls._gather_include(queryparams),
            'accept_mediatype': _get_single_value(queryparams, QueryparamName('acceptMediatype')),
        }

    def to_querystring(self) -> str:
        return self.to_querydict().urlencode()

    def to_querydict(self) -> QueryDict:
        # subclasses should override and add their fields to super().to_querydict()
        _querydict = QueryDict(mutable=True)
        if self.accept_mediatype:
            _querydict['acceptMediatype'] = self.accept_mediatype
        # TODO: self.iri_shorthand, self.include
        return _querydict

    @classmethod
    def _gather_shorthand(cls, queryparams: QueryparamDict):
        _prefixmap = {}
        for _qp_name, _iri in queryparams.get('iriShorthand', []):
            try:
                (_shortname,) = _qp_name.bracketed_names
            except ValueError:
                raise trove_exceptions.InvalidQueryParamName(_qp_name)
            else:
                _prefixmap[_shortname] = _iri
        return NAMESPACES_SHORTHAND.with_update(_prefixmap)

    @classmethod
    def _gather_include(cls, queryparams: QueryparamDict):
        # TODO: for _qp_name, _iri in queryparams.get('include', []):
        return frozenset()


@dataclasses.dataclass(frozen=True)
class Textsegment:
    text: str
    is_fuzzy: bool = True
    is_negated: bool = False
    is_openended: bool = False
    propertypath_set: frozenset[tuple[str, ...]] = DEFAULT_PROPERTYPATH_SET

    def __post_init__(self):
        if self.is_negated and self.is_fuzzy:
            raise trove_exceptions.InvalidSearchText(self.text, "search cannot be both negated and fuzzy")

    def words(self):
        return self.text.split()

    @classmethod
    def from_queryparam_family(cls, queryparams: QueryparamDict, queryparam_family: str):
        return frozenset(cls.iter_from_queryparam_family(queryparams, queryparam_family))

    @classmethod
    def iter_from_queryparam_family(cls, queryparams: QueryparamDict, queryparam_family: str):
        for (_param_name, _param_value) in queryparams.get(queryparam_family, ()):
            yield from cls.iter_from_searchtext_param(_param_name, _param_value)

    @classmethod
    def iter_from_searchtext_param(cls, param_name: QueryparamName, param_value: str):
        _propertypath_set = (
            _parse_propertypath_set(param_name.bracketed_names[0])
            if param_name.bracketed_names
            else None
        )
        for _textsegment in cls.iter_from_text(param_value):
            if _propertypath_set:
                yield dataclasses.replace(_textsegment, propertypath_set=_propertypath_set)
            else:
                yield _textsegment

    @classmethod
    def iter_from_text(cls, text: str) -> typing.Iterable['Textsegment']:
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

    @classmethod
    def queryparams_from_textsegments(self, queryparam_family: str, textsegments):
        _by_propertypath_set = collections.defaultdict(set)
        for _textsegment in textsegments:
            _by_propertypath_set[_textsegment.propertypath_set].add(_textsegment)
        for _propertypath_set, _combinable_segments in _by_propertypath_set.items():
            _qp_name = QueryparamName(
                queryparam_family,
                (propertypath_set_key(_propertypath_set),),
            )
            _qp_value = ' '.join(
                _textsegment.as_searchtext()
                for _textsegment in _combinable_segments
            )
            yield str(_qp_name), _qp_value

    def as_searchtext(self) -> str:
        _text = self.text
        if not self.is_fuzzy:
            _text = f'"{_text}"'
        if self.is_negated:
            _text = f'-{_text}'
        return _text


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
        def from_shortname(cls, shortname):
            _iri = trove_shorthand().expand_iri(shortname)
            return cls(_iri)

        def to_shortname(self) -> str:
            return trove_shorthand().compact_iri(self.value)

        def is_date_operator(self):
            return self in (self.BEFORE, self.AFTER, self.AT_DATE)

        def is_iri_operator(self):
            return self in (self.ANY_OF, self.NONE_OF)

        def is_valueless_operator(self):
            return self in (self.IS_PRESENT, self.IS_ABSENT)

    operator: FilterOperator
    value_set: frozenset[str]
    propertypath_set: frozenset[tuple[str, ...]] = DEFAULT_PROPERTYPATH_SET

    @classmethod
    def from_queryparam_family(cls, queryparams: QueryparamDict, queryparam_family: str):
        return frozenset(
            cls.from_filter_param(param_name, param_value)
            for (param_name, param_value)
            in queryparams.get(queryparam_family, ())
        )

    @classmethod
    def from_filter_param(cls, param_name: QueryparamName, param_value: str):
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
        _propertypath_set = _parse_propertypath_set(_serialized_path_set)
        _is_date_filter = all(
            is_date_property(_path[-1])
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
                    _value_list.append(osfmap_shorthand().expand_iri(_value))
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

    def as_queryparam(self, queryparam_family: str):
        _qp_name = QueryparamName(queryparam_family, (
            propertypath_set_key(self.propertypath_set),
            self.operator.to_shortname(),
        ))
        _qp_value = join_queryparam_value(
            osfmap_shorthand().compact_iri(_value)
            for _value in self.value_set
        )
        return str(_qp_name), _qp_value


@dataclasses.dataclass(frozen=True)
class SortParam:
    property_iri: str
    descending: bool = False

    @classmethod
    def sortlist_as_queryparam_value(cls, sort_params):
        return join_queryparam_value(
            _sort.as_queryparam_value()
            for _sort in sort_params
        )

    @classmethod
    def from_queryparams(cls, queryparams: QueryparamDict) -> tuple['SortParam', ...]:
        _paramvalue = _get_single_value(queryparams, QueryparamName('sort'))
        if not _paramvalue or _paramvalue == '-relevance':
            return ()
        return tuple(cls._from_sort_param_str(_paramvalue))

    @classmethod
    def _from_sort_param_str(cls, param_value: str) -> typing.Iterable['SortParam']:
        for _sort in split_queryparam_value(param_value):
            _sort_property = _sort.lstrip(DESCENDING_SORT_PREFIX)
            _property_iri = osfmap_shorthand().expand_iri(_sort_property)
            if not is_date_property(_property_iri):
                raise trove_exceptions.InvalidQueryParamValue('sort', _sort_property, "may not sort on non-date properties")
            yield cls(
                property_iri=_property_iri,
                descending=param_value.startswith(DESCENDING_SORT_PREFIX),
            )

    def as_queryparam_value(self):
        _key = propertypath_key((self.property_iri,))
        if self.descending:
            return f'-{_key}'
        return _key


@dataclasses.dataclass(frozen=True)
class PageParam:
    cursor: str | None  # intentionally opaque; for IndexStrategy to generate/interpret
    size: int | None = None  # size is None iff cursor is not None

    @classmethod
    def from_queryparams(cls, queryparams: QueryparamDict) -> 'PageParam':
        _cursor = _get_single_value(queryparams, QueryparamName('page', ('cursor',)))
        if _cursor:
            return cls(cursor=_cursor)
        _size = int(  # TODO: 400 response on non-int value
            _get_single_value(queryparams, QueryparamName('page', ('size',)))
            or DEFAULT_PAGE_SIZE
        )
        return cls(size=min(_size, MAX_PAGE_SIZE), cursor=None)


@dataclasses.dataclass(frozen=True)
class CardsearchParams(BaseTroveParams):
    cardsearch_textsegment_set: frozenset[Textsegment]
    cardsearch_filter_set: frozenset[SearchFilter]
    index_strategy_name: str | None
    sort_list: tuple[SortParam]
    page: PageParam
    related_property_paths: tuple[tuple[str, ...]]
    unnamed_iri_values: frozenset[str]

    @classmethod
    def parse_queryparams(cls, queryparams: QueryparamDict) -> dict:
        _filter_set = SearchFilter.from_queryparam_family(queryparams, 'cardSearchFilter')
        return {
            **super().parse_queryparams(queryparams),
            'cardsearch_textsegment_set': Textsegment.from_queryparam_family(queryparams, 'cardSearchText'),
            'cardsearch_filter_set': _filter_set,
            'index_strategy_name': _get_single_value(queryparams, QueryparamName('indexStrategy')),
            'sort_list': SortParam.from_queryparams(queryparams),
            'page': PageParam.from_queryparams(queryparams),
            'include': None,  # TODO
            'related_property_paths': _get_related_property_paths(_filter_set),
            'unnamed_iri_values': frozenset(),  # TODO: frozenset(_get_unnamed_iri_values(_filter_set)),
        }

    def to_querydict(self) -> QueryDict:
        _querydict = super().to_querydict()
        for _qp_name, _qp_value in Textsegment.queryparams_from_textsegments('cardSearchText', self.cardsearch_textsegment_set):
            _querydict[_qp_name] = _qp_value
        if self.sort_list:
            _querydict['sort'] = SortParam.sortlist_as_queryparam_value(self.sort_list)
        if self.page.cursor:
            _querydict['page[cursor]'] = self.page.cursor
        elif self.page.size != DEFAULT_PAGE_SIZE:
            _querydict['page[size]'] = self.page.size
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
    valuesearch_propertypath: tuple[str, ...]
    valuesearch_textsegment_set: frozenset[Textsegment]
    valuesearch_filter_set: frozenset[SearchFilter]

    # override CardsearchParams
    @classmethod
    def parse_queryparams(cls, queryparams: QueryparamDict) -> dict:
        _raw_propertypath = _get_single_value(queryparams, QueryparamName('valueSearchPropertyPath'))
        if not _raw_propertypath:
            raise trove_exceptions.MissingRequiredQueryParam('valueSearchPropertyPath')
        return {
            **super().parse_queryparams(queryparams),
            'valuesearch_propertypath': _parse_propertypath(_raw_propertypath, allow_globs=False),
            'valuesearch_textsegment_set': Textsegment.from_queryparam_family(queryparams, 'valueSearchText'),
            'valuesearch_filter_set': SearchFilter.from_queryparam_family(queryparams, 'valueSearchFilter'),
        }

    def to_querydict(self):
        _querydict = super().to_querydict()
        _querydict['valueSearchPropertyPath'] = propertypath_key(self.valuesearch_propertypath)
        for _qp_name, _qp_value in Textsegment.queryparams_from_textsegments('valueSearchText', self.valuesearch_textsegment_set):
            _querydict[_qp_name] = _qp_value
        for _filter in self.valuesearch_filter_set:
            _qp_name, _qp_value = _filter.as_queryparam('valueSearchFilter')
            _querydict.appendlist(_qp_name, _qp_value)
        return _querydict

    def valuesearch_iris(self):
        for _filter in self.valuesearch_filter_set:
            if _filter.is_sameas_filter():
                yield from _filter.value_set

    def valuesearch_type_iris(self):
        for _filter in self.valuesearch_filter_set:
            if _filter.is_type_filter():
                yield from _filter.value_set


###
# helper functions

def is_globpath(path: tuple[str, ...]) -> bool:
    return all(_pathstep == GLOB_PATHSTEP for _pathstep in path)


def make_globpath(length: int) -> tuple[str, ...]:
    return ONE_GLOB_PROPERTYPATH * length


def propertypathstep_key(pathstep: str) -> str:
    if pathstep == GLOB_PATHSTEP:
        return pathstep
    # assume iri
    return urllib.parse.quote(osfmap_shorthand().compact_iri(pathstep))


def propertypath_key(property_path: tuple[str, ...]) -> str:
    return PROPERTYPATH_DELIMITER.join(
        propertypathstep_key(_pathstep)
        for _pathstep in property_path
    )


def propertypath_set_key(propertypath_set: frozenset[tuple[str, ...]]) -> str:
    return join_queryparam_value(
        propertypath_key(_propertypath)
        for _propertypath in propertypath_set
    )


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
        raise trove_exceptions.InvalidRepeatedQueryParam(str(queryparam_name))
    else:
        return _singlevalue


def _parse_propertypath_set(serialized_path_set: str, *, allow_globs=True) -> frozenset[tuple[str, ...]]:
    # comma-delimited set of dot-delimited paths
    return frozenset(
        _parse_propertypath(_path, allow_globs=allow_globs)
        for _path in split_queryparam_value(serialized_path_set)
    )


def _parse_propertypath(serialized_path: str, *, allow_globs=True) -> tuple[str, ...]:
    _path = tuple(
        osfmap_shorthand().expand_iri(_pathstep)
        for _pathstep in serialized_path.split(PROPERTYPATH_DELIMITER)
    )
    if GLOB_PATHSTEP in _path:
        if not allow_globs:
            raise trove_exceptions.InvalidPropertyPath(serialized_path, 'no * allowed')
        if any(_pathstep != GLOB_PATHSTEP for _pathstep in _path):
            raise trove_exceptions.InvalidPropertyPath(
                serialized_path,
                f'path must be all * or no * (got {serialized_path})',
            )
    return _path


def _get_related_property_paths(filter_set) -> tuple[tuple[str, ...], ...]:
    # hard-coded for osf.io search pages, static list per type
    # TODO: replace with some dynamism, maybe a 'significant_terms' aggregation
    _type_iris = set()
    for _filter in filter_set:
        if _filter.is_type_filter():
            _type_iris.update(_filter.value_set)
    return suggested_property_paths(_type_iris)


def _get_unnamed_iri_values(filter_set) -> typing.Iterable[str]:
    for _filter in filter_set:
        if _filter.operator.is_iri_operator():
            for _iri in _filter.value_set:
                if _iri not in OSFMAP_THESAURUS:
                    yield _iri
