from __future__ import annotations
import csv
import functools
import dataclasses
import typing

from primitive_metadata import primitive_rdf as rdf

from ._simple_osfmap import BaseSimpleOsfmapRenderer


Jsonpath = tuple[str, ...]  # path of json keys

_MULTIVALUE_DELIMITER = ' ; '  # possible improvement: smarter in-value delimiting?


class TrovesearchTsvRenderer(BaseSimpleOsfmapRenderer):
    MEDIATYPE = 'text/tab-separated-values'
    _CSV_DIALECT = csv.excel_tab

    def render_unicard_document(self, card_iri: str, osfmap_json: dict):
        self.render_multicard_document([(card_iri, osfmap_json)])

    def render_multicard_document(self, cards: typing.Iterable[tuple[str, dict]]):
        # possible optimization: StreamingHttpResponse (to be worthwhile, should
        # support streaming all the way from asgi thru gathering and index strategy)
        _doc = TabularDoc(cards)
        _writer = self._get_csv_writer()
        _writer.writerow(_doc.header())
        _writer.writerows(_doc.rows())

    def _get_csv_writer(self):
        return csv.writer(self.http_response, dialect=self._CSV_DIALECT)


@dataclasses.dataclass
class TabularDoc:
    cards: typing.Iterable[tuple[str, dict]]

    @functools.cached_property
    def field_paths(self) -> tuple[Propertypath]:
        _pathset = set()
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

    def _row_field_value(self, osfmap_json: dict, field_path: Propertypath) -> str:
        _obj_set = _getattrpath(osfmap_json, field_path)
        return _MULTIVALUE_DELIMITER.join(
            self._rdfobj_to_valuestr(_obj)
            for _obj in _obj_set
        )

    def _rdfobj_to_valuestr(self, obj: rdf.RdfObject) -> str:
        ...


def _osfmap_tabular_paths(osfmap_json: dict) -> Iterator[Jsonpath]:
    ...

def _should_render_tabularly(osfmap_json: dict, path: Propertypath):

def _osfmap_keys(osfmap_json: dict):
