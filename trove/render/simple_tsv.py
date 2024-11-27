from __future__ import annotations
import csv
import functools
import dataclasses
import typing

from trove.vocab import mediatypes
from trove.vocab import osfmap
from trove.vocab.namespaces import TROVE
from ._simple_trovesearch import SimpleTrovesearchRenderer
from ._rendering import StreamableRendering


Jsonpath = typing.Iterable[str]  # path of json keys

_MULTIVALUE_DELIMITER = ' ; '  # possible improvement: smarter in-value delimiting?
_VALUE_KEY_PREFERENCE = ('@value', '@id', 'name', 'prefLabel', 'label')


class TrovesearchSimpleTsvRenderer(SimpleTrovesearchRenderer):
    MEDIATYPE = mediatypes.TAB_SEPARATED_VALUES
    INDEXCARD_DERIVER_IRI = TROVE['derive/osfmap_json']
    CSV_DIALECT: type[csv.Dialect] = csv.excel_tab

    def unicard_rendering(self, card_iri: str, osfmap_json: dict):
        self.multicard_rendering(cards=[(card_iri, osfmap_json)])

    def multicard_rendering(self, cards: typing.Iterable[tuple[str, dict]]):
        _doc = TabularDoc(list(cards))  # TODO: static column header, actual stream
        return StreamableRendering(
            mediatype=self.MEDIATYPE,
            content_stream=csv_stream(self.CSV_DIALECT, _doc.header(), _doc.rows()),
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
        # TODO: use jsonapi's "sparse fieldsets" to allow selecting
        #       https://jsonapi.org/format/#fetching-sparse-fieldsets
        return tuple((
            ('@id',),
            *self._nonempty_field_paths()
        ))

    def header(self) -> list[str]:
        return ['.'.join(_path) for _path in self.field_paths]

    def rows(self) -> typing.Iterator[list[str]]:
        for _card_iri, _osfmap_json in self.cards:
            yield self._row_values(_osfmap_json)

    def _nonempty_field_paths(self) -> typing.Iterator[Jsonpath]:
        for _path in osfmap.DEFAULT_TABULAR_SEARCH_COLUMN_PATHS:
            _jsonpath = _osfmap_jsonpath(_path)
            _path_is_present = any(
                _has_value(_card, _jsonpath)
                for (_, _card) in self.cards
            )
            if _path_is_present:
                yield _jsonpath

    def _row_values(self, osfmap_json: dict) -> list[str]:
        return [
            self._row_field_value(osfmap_json, _field_path)
            for _field_path in self.field_paths
        ]

    def _row_field_value(self, osfmap_json: dict, field_path: Jsonpath) -> str:
        return _MULTIVALUE_DELIMITER.join(
            _render_tabularly(_obj)
            for _obj in _iter_values(osfmap_json, field_path)
        )


def _osfmap_jsonpath(iri_path: typing.Iterable[str]) -> Jsonpath:
    _shorthand = osfmap.osfmap_shorthand()
    return tuple(
        _shorthand.compact_iri(_pathstep)
        for _pathstep in iri_path
    )


def _has_value(osfmap_json: dict, path: Jsonpath) -> bool:
    try:
        next(_iter_values(osfmap_json, path))
    except StopIteration:
        return False
    else:
        return True


def _iter_values(osfmap_json: dict, path: Jsonpath) -> typing.Iterator:
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
        elif _val is not None:
            yield _val


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
