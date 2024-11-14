from __future__ import annotations
import csv
import functools
import dataclasses
import typing

from trove.vocab import mediatypes
from trove.vocab.osfmap import (
    osfmap_shorthand,
    SKIPPABLE_PROPERTIES
)
from trove.vocab.namespaces import TROVE
from ._simple_trovesearch import SimpleTrovesearchRenderer
from ._rendering import StreamableRendering


Jsonpath = tuple[str, ...]  # path of json keys

_MULTIVALUE_DELIMITER = ' ; '  # possible improvement: smarter in-value delimiting?
_VALUE_KEY_PREFERENCE = ('@value', '@id', 'name', 'prefLabel', 'label')
_SKIPPABLE_KEYS = {osfmap_shorthand().compact_iri(_iri) for _iri in SKIPPABLE_PROPERTIES}


class TrovesearchSimpleTsvRenderer(SimpleTrovesearchRenderer):
    MEDIATYPE = mediatypes.TAB_SEPARATED_VALUES
    INDEXCARD_DERIVER_IRI = TROVE['derive/osfmap_json']
    _CSV_DIALECT: type[csv.Dialect] = csv.excel_tab

    def unicard_rendering(self, card_iri: str, osfmap_json: dict):
        self.multicard_rendering(cards=[(card_iri, osfmap_json)])

    def multicard_rendering(self, cards: typing.Iterable[tuple[str, dict]]):
        _doc = TabularDoc(list(cards))  # TODO: static column header, actual stream
        return StreamableRendering(
            mediatype=self.MEDIATYPE,
            content_stream=csv_stream(self._CSV_DIALECT, _doc.header(), _doc.rows()),
        )


def csv_stream(csv_dialect, header: list, rows: typing.Iterator[list]) -> typing.Iterator[str]:
    _writer = csv.writer(_Echo(), dialect=csv_dialect)
    yield _writer.writerow(header)
    for _row in rows:
        yield _writer.writerow(_row)


@dataclasses.dataclass
class TabularDoc:
    cards: typing.Iterable[tuple[str, dict]]

    @functools.cached_property
    def field_paths(self) -> tuple[Jsonpath, ...]:
        _pathset: set[Jsonpath] = set()
        for _, _osfmap_json in self.cards:
            _pathset.update(_osfmap_tabular_paths(_osfmap_json))
        return tuple(sorted(_pathset, key=lambda _path: (len(_path), _path)))

    def header(self) -> list[str]:
        return ['.'.join(_path) for _path in self.field_paths]

    def rows(self) -> typing.Iterator[list[str]]:
        for _card_iri, _osfmap_json in self.cards:
            yield self._row_values(_osfmap_json)

    def _row_values(self, osfmap_json: dict) -> list[str]:
        return [
            self._row_field_value(osfmap_json, _field_path)
            for _field_path in self.field_paths
        ]

    def _row_field_value(self, osfmap_json: dict, field_path: Jsonpath) -> str:
        return _MULTIVALUE_DELIMITER.join(
            _render_tabularly(_obj)
            for _obj in _iter_values(osfmap_json, field_path)
            if _obj is not None
        )


def _osfmap_tabular_paths(osfmap_json: dict) -> typing.Iterator[Jsonpath]:
    # currently simple: paths of length one
    for _key, _value in osfmap_json.items():
        if (_key not in _SKIPPABLE_KEYS) and _should_render_tabularly(_value):
            yield (_key,)


def _iter_values(osfmap_json: dict, path: typing.Iterable[str]) -> typing.Iterator:
    assert path
    (_step, *_rest) = path
    _val = osfmap_json.get(_step)
    if _rest:
        if isinstance(_val, dict):
            yield from _iter_values(_val, _rest)
        elif isinstance(_val, list):
            for _val_obj in _val:
                yield from _iter_values(_val_obj, _rest)
    else:
        if isinstance(_val, list):
            yield from _val
        else:
            yield _val


def _should_render_tabularly(osfmap_json_value) -> bool:
    if isinstance(osfmap_json_value, (str, int, float)):
        return True
    if isinstance(osfmap_json_value, dict) and any(
        _key in osfmap_json_value
        for _key in _VALUE_KEY_PREFERENCE
    ):
        return True
    if isinstance(osfmap_json_value, list) and any(
        _should_render_tabularly(_val)
        for _val in osfmap_json_value
    ):
        return True
    return False


def _render_tabularly(json_val):
    if isinstance(json_val, (str, int, float)):
        return json_val
    if isinstance(json_val, dict):
        for _key in _VALUE_KEY_PREFERENCE:
            _val = json_val.get(_key)
            if isinstance(_val, list):
                return (
                    _render_tabularly(_val[0])
                    if _val
                    else None
                )
            if _val is not None:
                return _val
    return None


class _Echo:
    '''a write-only file-like object, to convince `csv.csvwriter.writerow` to return strings

    from https://docs.djangoproject.com/en/5.1/howto/outputting-csv/#streaming-large-csv-files
    '''
    def write(self, line: str):
        return line
