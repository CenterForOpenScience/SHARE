from __future__ import annotations
import collections
import dataclasses
import itertools
import re
import typing

# TODO: remove django dependency (tho it is convenient)
from django.http import QueryDict
from primitive_metadata import primitive_rdf as rdf

from trove import exceptions as trove_exceptions
from trove.util.frozen import freeze
from trove.util.propertypath import (
    PropertypathSet,
    Propertypath,
    PropertypathParser,
)
from trove.vocab.namespaces import NAMESPACES_SHORTHAND


###
# jsonapi query parameter parsing:
# https://jsonapi.org/format/#query-parameters
QUERYPARAM_FAMILY_REGEX = re.compile(
    r'^[a-zA-Z0-9]'     # initial alphanumeric,
    r'[-_a-zA-Z0-9]*'   # - and _ ok from then,
    r'(?=\[|$)'         # followed by [ or end.
)
QUERYPARAM_FAMILYMEMBER_REGEX = re.compile(
    r'\['                   # start with open square-bracket,
    r'(?P<name>[^[\]]*)'    # anything not square-bracket (note: less strict than jsonapi)
    r'\]'                   # end with close-bracket
)
# is common (but not required) for a query parameter
# value to be split on commas, used as a list or set
QUERYPARAM_VALUES_DELIM = ','


@dataclasses.dataclass(frozen=True)
class QueryparamName:
    family: str
    bracketed_names: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.bracketed_names, tuple):
            super().__setattr__('bracketed_names', tuple(self.bracketed_names))

    @classmethod
    def from_str(cls, queryparam_name: str) -> 'QueryparamName':
        family_match = QUERYPARAM_FAMILY_REGEX.match(queryparam_name)
        if not family_match:
            raise trove_exceptions.InvalidQueryParamName(queryparam_name)
        family = family_match.group()
        next_position = family_match.end()
        bracketed_names = []
        while next_position < len(queryparam_name):
            bracketed_match = QUERYPARAM_FAMILYMEMBER_REGEX.match(queryparam_name, next_position)
            if not bracketed_match:
                raise trove_exceptions.InvalidQueryParamName(queryparam_name)
            bracketed_names.append(bracketed_match.group('name') or '')
            next_position = bracketed_match.end()
        if next_position != len(queryparam_name):
            raise trove_exceptions.InvalidQueryParamName(queryparam_name)
        return cls(family, tuple(bracketed_names))

    def __str__(self):
        return ''.join((
            self.family,
            *(
                f'[{bracketed_name}]'
                for bracketed_name in self.bracketed_names
            ),
        ))


QueryparamDict = dict[
    str,  # keyed by queryparam family
    list[tuple[QueryparamName, str]],
]


def queryparams_from_querystring(querystring: str) -> QueryparamDict:
    _queryparams: QueryparamDict = {}
    _querydict = QueryDict(querystring)
    for _unparsed_name, _param_value_list in _querydict.lists():
        _parsed_name = QueryparamName.from_str(_unparsed_name)
        for _param_value in _param_value_list:
            (
                _queryparams
                .setdefault(_parsed_name.family, [])
                .append((_parsed_name, _param_value))
            )
    return _queryparams


def split_queryparam_value(value: str):
    return value.split(QUERYPARAM_VALUES_DELIM)


def join_queryparam_value(values: typing.Iterable[str]):
    return QUERYPARAM_VALUES_DELIM.join(values)


def get_single_value(
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


@dataclasses.dataclass(frozen=True)
class BaseTroveParams:
    iri_shorthand: rdf.IriShorthand = dataclasses.field(repr=False)
    accept_mediatype: str | None
    included_relations: PropertypathSet = dataclasses.field(repr=False, compare=False)
    attrpaths_by_type: collections.abc.Mapping[str, PropertypathSet] = dataclasses.field(repr=False, compare=False)

    ###
    # class methods

    @classmethod
    def from_querystring(cls, querystring: str) -> typing.Self:
        return cls.from_queryparams(queryparams_from_querystring(querystring))

    @classmethod
    def from_queryparams(cls, queryparams: QueryparamDict) -> typing.Self:
        return cls(**cls.parse_queryparams(queryparams))

    @classmethod
    def parse_queryparams(cls, queryparams: QueryparamDict) -> dict:
        # subclasses should override and add their fields to super().parse_queryparams(queryparams)
        _shorthand = cls._gather_shorthand(queryparams)
        return {
            'iri_shorthand': _shorthand,
            'included_relations': cls._gather_included_relations(queryparams, _shorthand),
            'attrpaths_by_type': cls._gather_attrpaths(queryparams, _shorthand),
            'accept_mediatype': get_single_value(queryparams, QueryparamName('acceptMediatype')),
        }

    @classmethod
    def _default_shorthand(cls) -> rdf.IriShorthand:
        return NAMESPACES_SHORTHAND

    @classmethod
    def _default_include(cls) -> PropertypathSet:
        return frozenset()

    @classmethod
    def _default_attrpaths(cls) -> dict[str, tuple[Propertypath, ...]]:
        return {}

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
        _shorthand = cls._default_shorthand()
        if _prefixmap:
            _shorthand = _shorthand.with_update(_prefixmap)
        return _shorthand

    @classmethod
    def _gather_included_relations(cls, queryparams: QueryparamDict, shorthand: rdf.IriShorthand) -> PropertypathSet:
        _include_params = queryparams.get('include', [])
        if _include_params:
            return frozenset(itertools.chain.from_iterable(
                parse_propertypaths(_include_value, shorthand)
                for _, _include_value in _include_params
            ))
        return cls._default_include()

    @classmethod
    def _gather_attrpaths(cls, queryparams: QueryparamDict, shorthand: rdf.IriShorthand) -> collections.abc.Mapping[
        str,
        tuple[Propertypath, ...],
    ]:
        _attrpaths: collections.ChainMap[str, tuple[Propertypath, ...]] = collections.ChainMap(
            cls._default_attrpaths(),
        )
        _fields_params = queryparams.get('fields', [])
        if _fields_params:
            _requested: dict[str, list[Propertypath]] = collections.defaultdict(list)
            for _param_name, _param_value in _fields_params:
                try:
                    (_typenames,) = filter(bool, _param_name.bracketed_names)
                except (IndexError, ValueError):
                    raise trove_exceptions.InvalidQueryParamName(
                        f'expected "fields[TYPE]" (with exactly one non-empty bracketed segment)'
                        f' (got "{_param_name}")'
                    )
                else:
                    for _type in split_queryparam_value(_typenames):
                        _type_iri = shorthand.expand_iri(_type)
                        _requested[_type_iri].extend(parse_propertypaths(_param_value, shorthand))
            _attrpaths = _attrpaths.new_child(freeze(_requested))
        return _attrpaths

    ###
    # instance methods

    def to_querystring(self) -> str:
        return self.to_querydict().urlencode()

    def to_querydict(self) -> QueryDict:
        # subclasses should override and add their fields to super().to_querydict()
        _querydict = QueryDict(mutable=True)
        if self.accept_mediatype:
            _querydict['acceptMediatype'] = self.accept_mediatype
        # TODO: iriShorthand, include, fields[...]
        return _querydict


def parse_propertypaths(serialized_path_set: str, shorthand: rdf.IriShorthand) -> typing.Iterator[Propertypath]:
    _parser = PropertypathParser(shorthand)
    for _path in split_queryparam_value(serialized_path_set):
        yield _parser.parse_propertypath(_path)
