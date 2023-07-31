import dataclasses
import re
import urllib

# TODO: remove django dependency (tho it is convenient)
from django.http import QueryDict


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
    r'(?P<name>[^[\]]*)'    # anything not square-bracket
    r'\]'                   # end with close-bracket
)
# is common (but not required) for a query parameter
# value to be split on commas, used as a list or set
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
            bracketed_names.append(bracketed_match.group('name') or '')
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


JsonapiQueryparamDict = dict[
    str,  # keyed by queryparam family
    list[tuple[JsonapiQueryparamName, str]],
]


def queryparams_from_iri(iri: str) -> JsonapiQueryparamDict:
    _parsed_iri = urllib.parse.urlparse(iri)
    return queryparams_from_querystring(_parsed_iri.query)


def queryparams_from_querystring(querystring: str) -> JsonapiQueryparamDict:
    _queryparams: JsonapiQueryparamDict = {}
    _querydict = QueryDict(querystring)
    for _unparsed_name, _param_value_list in _querydict.lists():
        _parsed_name = JsonapiQueryparamName.from_str(_unparsed_name)
        for _param_value in _param_value_list:
            (
                _queryparams
                .setdefault(_parsed_name.family, [])
                .append((_parsed_name, _param_value))
            )
    return _queryparams


def split_queryparam_value(value: str):
    return value.split(QUERYPARAM_VALUES_DELIM)
