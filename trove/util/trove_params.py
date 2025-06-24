from __future__ import annotations
from collections import defaultdict
import dataclasses
import typing
if typing.TYPE_CHECKING:
    from collections.abc import Mapping

# TODO: remove django dependency (tho it is convenient)
from django.http import QueryDict
from primitive_metadata import primitive_rdf as rdf

from trove import exceptions as trove_exceptions
from trove.util.chainmap import SimpleChainMap
from trove.util.frozen import freeze
from trove.util.propertypath import (
    PropertypathSet,
    Propertypath,
    parse_propertypath, GLOB_PATHSTEP,
)
from trove.util import queryparams as _qp
from trove.vocab.namespaces import namespaces_shorthand


@dataclasses.dataclass(frozen=True)
class BasicTroveParams:
    iri_shorthand: rdf.IriShorthand = dataclasses.field(repr=False)
    accept_mediatype: str | None
    included_relations: PropertypathSet = dataclasses.field(repr=False, compare=False)
    attrpaths_by_type: Mapping[str, PropertypathSet] = dataclasses.field(repr=False, compare=False)
    blend_cards: bool

    ###
    # class methods

    @classmethod
    def from_querystring(cls, querystring: str) -> typing.Self:
        return cls.from_queryparams(_qp.queryparams_from_querystring(querystring))

    @classmethod
    def from_queryparams(cls, queryparams: _qp.QueryparamDict) -> typing.Self:
        return cls(**cls.parse_queryparams(queryparams))

    @classmethod
    def parse_queryparams(cls, queryparams: _qp.QueryparamDict) -> dict:
        # subclasses should override and add their fields to super().parse_queryparams(queryparams)
        _shorthand = cls._gather_shorthand(queryparams)
        return {
            'iri_shorthand': _shorthand,
            'included_relations': cls._gather_included_relations(queryparams, _shorthand),
            'attrpaths_by_type': cls._gather_attrpaths(queryparams, _shorthand),
            'accept_mediatype': _qp.get_single_value(queryparams, 'acceptMediatype'),
            'blend_cards': _qp.get_bool_value(queryparams, 'blendCards'),
        }

    @classmethod
    def _default_shorthand(cls) -> rdf.IriShorthand:
        return namespaces_shorthand()

    @classmethod
    def _default_include(cls) -> PropertypathSet:
        return frozenset()

    @classmethod
    def _default_attrpaths(cls) -> Mapping[str, tuple[Propertypath, ...]]:
        return {}

    @classmethod
    def _gather_shorthand(cls, queryparams: _qp.QueryparamDict):
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
    def _gather_included_relations(cls, queryparams: _qp.QueryparamDict, shorthand: rdf.IriShorthand) -> PropertypathSet:
        _include_params = queryparams.get('include', [])
        if _include_params:
            return frozenset((
                parse_propertypath(_path_value, shorthand)
                for _, _include_value in _include_params
                for _path_value in _qp.split_queryparam_value(_include_value)
            ))
        return cls._default_include()

    @classmethod
    def _gather_attrpaths(cls, queryparams: _qp.QueryparamDict, shorthand: rdf.IriShorthand) -> Mapping[
        str,
        tuple[Propertypath, ...],
    ]:
        _attrpaths = SimpleChainMap([cls._default_attrpaths()])
        _fields_params = queryparams.get('fields', [])
        if _fields_params:
            _requested: dict[str, list[Propertypath]] = defaultdict(list)
            for _param_name, _param_value in _fields_params:
                if _param_name.bracketed_names:  # e.g. "fields[TYPE1,TYPE2,TYPE3]=..."
                    _typenames = _qp.split_queryparam_value(_param_name.bracketed_names[0])
                else:  # omitted brackets equivalent to "fields[*]" (apply to any type)
                    _typenames = [GLOB_PATHSTEP]
                for _typename in _typenames:
                    if _typename != GLOB_PATHSTEP:
                        _typename = shorthand.expand_iri(_typename)
                    _requested[_typename].extend(
                        (  # list of field paths in query param value
                            parse_propertypath(_path_value, shorthand)
                            for _path_value in _qp.split_queryparam_value(_param_value)
                        )
                    )
            _attrpaths = _attrpaths.with_new(freeze(_requested))
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
        if self.blend_cards:
            _querydict['blendCards'] = ''
        # TODO: iriShorthand, include, fields[...]
        return _querydict
