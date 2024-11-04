from __future__ import annotations
import csv
import functools
import dataclasses
import typing

from ._simple_osfmap import BaseSimpleOsfmapRenderer


Jsonpath = tuple[str, ...]  # path of json keys

_MULTIVALUE_DELIMITER = ' ; '  # possible improvement: smarter in-value delimiting?
_VALUE_KEY_PREFERENCE = ('@value', '@id', 'name', 'prefLabel', 'label')


class TrovesearchTsvRenderer(BaseSimpleOsfmapRenderer):
    MEDIATYPE = 'text/tab-separated-values'
    _CSV_DIALECT = csv.excel_tab

    def render_unicard_document(self, card_iri: str, osfmap_json: dict):
        self.render_multicard_document(cards=[(card_iri, osfmap_json)])

    def render_multicard_document(self, cards: typing.Iterable[tuple[str, dict]]):
        # possible optimization: StreamingHttpResponse (to be worthwhile, should
        # support streaming all the way from asgi thru gathering and index strategy)
        _writer = csv.writer(self.http_response, dialect=self._CSV_DIALECT)
        _doc = TabularDoc(cards)
        _writer.writerow(_doc.header())
        _writer.writerows(_doc.rows())


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
    for _key, _value in osfmap_json.items():
        if _should_render_tabularly(_value):
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
            if _val is not None:
                return _val[_key]
    return None
