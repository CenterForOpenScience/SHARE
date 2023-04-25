import dataclasses
import enum
import re
import typing

from django import http
import rdflib

from share.search import exceptions


QUERYPARAM_FAMILY_REGEX = re.compile(r'^[a-zA-Z0-9][-_a-zA-Z0-9]*(?>\[|$)')
QUERYPARAM_MEMBER_REGEX = re.compile(r'\[(?P<member_name>[a-zA-Z0-9][-_a-zA-Z0-9]*)?\]')
QUERYPARAM_VALUES_DELIM = ','


class FilterOperator(enum.StrEnum):
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
                for bracketed_name in bracketed_names
            ),
        ))


@dataclasses.dataclass(frozen=True)
class SearchFilter:
    filter_family: str
    property_path: tuple[rdflib.URIRef]
    value_set: frozenset[str]
    operator: str

    @classmethod
    def from_filter_param(cls, param_name: JsonapiQueryparamName, param_value: str):
        try:  # "filter[<serialized_path>][<operator>]"
            (serialized_path, operator) = param_name.bracketed_names
        except ValueError:
            try:  # "filter[<serialized_path>]" (with default operator)
                (serialized_path,) = param_name.bracketed_names
                operator = FilterOperator.ANY_OF
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
    card_search_text_set: frozenset[str]
    card_search_filter_set: frozenset[SearchFilter]
    include: typing.Optional[frozenset[tuple[str]]] = None
    sort: typing.Optional[str] = None

    @classmethod
    def from_querydicts(cls, query_dicts: typing.Iterable[http.QueryDict]):
        queryparams = _jsonapi_queryparams(query_dicts)
        return cls(
            card_search_text_set=frozenset(
                param_value
                for _, param_value in queryparams['cardSearchText']  # TODO: more explicit name-map
            ),
            card_search_filter_set=frozenset(
                SearchFilter.from_filter_param(param_name, param_value)
                for (param_name, param_value) in queryparams['cardSearchFilter']
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


def _jsonapi_queryparams(querydicts: typing.Iterable[http.QueryDict]) -> dict[
        str,  # keyed by queryparam family
        list[tuple[JsonapiQueryparamName, str]],
]:
    by_family = {}
    for querydict in querydicts:
        for unparsed_param_name, param_value_list in querydict.lists():
            parsed_param_name = JsonapiQueryparamName.from_str(unparsed_param_name)
            for param_value in param_value_list:
                (
                    by_family
                    .setdefault(parsed_param_name.family, list)
                    .append((parsed_param_name, param_value))
                )
