from __future__ import annotations
from collections.abc import Iterable
import dataclasses
import re
from typing import Self

# TODO: remove django dependency (tho it is convenient)
from django.http import QueryDict

from trove import exceptions as trove_exceptions


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

TRUTHY_VALUES = frozenset(('t', 'true', '1', 'y', 'yes'))
FALSY_VALUES = frozenset(('f', 'false', '0', 'n', 'no'))


@dataclasses.dataclass(frozen=True)
class QueryparamName:
    family: str
    bracketed_names: tuple[str, ...] = ()

    @classmethod
    def from_str(cls, queryparam_name: str) -> Self:
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

    def __str__(self) -> str:
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


def split_queryparam_value(value: str) -> list[str]:
    return value.split(QUERYPARAM_VALUES_DELIM)


def join_queryparam_value(values: Iterable[str]) -> str:
    return QUERYPARAM_VALUES_DELIM.join(values)


def get_single_value(
    queryparams: QueryparamDict,
    queryparam_name: QueryparamName | str,
) -> str | None:
    if isinstance(queryparam_name, QueryparamName):
        _family_name = queryparam_name.family
        _expected_brackets = queryparam_name.bracketed_names
    else:
        _family_name = queryparam_name
        _expected_brackets = ()
    _paramvalues = [
        _paramvalue
        for _paramname, _paramvalue in queryparams.get(_family_name, ())
        if _paramname.bracketed_names == _expected_brackets
    ]
    if not _paramvalues:
        return None
    try:
        (_singlevalue,) = _paramvalues
    except ValueError:
        raise trove_exceptions.InvalidRepeatedQueryParam(str(queryparam_name))
    return _singlevalue


def get_bool_value(
    queryparams: QueryparamDict,
    queryparam_name: QueryparamName | str,
    *,
    if_absent: bool = False,  # by default, param absence is falsy
    if_empty: bool = True,  # by default, presence (with empty value) is truthy
) -> bool:
    return parse_booly_str(
        get_single_value(queryparams, queryparam_name),
        if_absent=if_absent,
        if_empty=if_empty,
    )


def parse_booly_str(
    value: str | None,
    *,
    if_absent: bool = False,  # by default, param absence is falsy
    if_empty: bool = True,  # by default, presence (with empty value) is truthy
) -> bool:
    if value is None:
        return if_absent
    if value == '':
        return if_empty
    _lowered = value.lower()
    if _lowered in TRUTHY_VALUES:
        return True
    if _lowered in FALSY_VALUES:
        return False
    raise ValueError(f'unboolable string: "{value}"')
