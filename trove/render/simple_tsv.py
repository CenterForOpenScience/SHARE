from __future__ import annotations
import csv
import dataclasses
import typing

from primitive_metadata import primitive_rdf as rdf

from trove.vocab.osfmap import osfmap_shorthand
from trove.vocab.namespaces import TROVE
from ._simple import BaseSimpleCardRenderer


Propertypath = tuple[str, ...]  # IRI path

_MULTIVALUE_DELIMITER = ' ; '  # possible improvement: smarter in-value delimiter handling?


class TrovesearchTsvRenderer(BaseSimpleCardRenderer):
    MEDIATYPE = 'text/tab-separated-values'
    INDEXCARD_DERIVER_IRI = None  # just the rdf, pls
    _CSV_DIALECT = csv.excel_tab
    iri_shorthand: rdf.IriShorthand = osfmap_shorthand()

    def render_unicard_document(self, card_iri, card_content):
        self.render_multicard_document([(card_iri, card_content)])

    def render_multicard_document(self, cards_iris_and_contents):
        # possible optimization: StreamingHttpResponse (to be worthwhile, should
        # support streaming all the way from asgi thru gathering and index strategy)
        _doc = TabularDoc(cards_iris_and_contents)
        _writer = csv.writer(self.response, dialect=self._CSV_DIALECT)
        _writer.writerow(_doc.header())
        _writer.writerows(_doc.rows())

    def _header_paths(cards: Iterable[QuotedGraph]) -> tuple[Propertypath]:
        ...

@dataclasses.dataclass
class TabularDoc:
    cards_iris_and_contents: Iterable[str, QuotedGraph]

    @functools.cached_property
    def field_paths(self) -> tuple[Propertypath]:
        ...

    def header(self) -> list[str]:
        return list(self.field_paths_by_header.keys())

    def rows(self) -> typing.Iterator[list[str]]:
        for _row_focus_iri in self.rdf_graph.q(self.root_focus_iri, self.tabular_focus_path):
            yield self._row_values(_row_focus_iri)

    def _row_values(self, row_focus_iri: str) -> list[str]:
        return [
            self._row_field_value(row_focus_iri, _field_path)
            for _field_path in self.field_paths_by_header.values()
        ]

    def _row_field_value(self, row_focus_iri: str, field_path: Propertypath) -> str:
        _obj_set = set(self.rdf_graph.q(row_focus_iri, field_path))
        return _MULTIVALUE_DELIMITER.join(
            self._rdfobj_to_valuestr(_obj)
            for _obj in _obj_set
        )

    def _rdfobj_to_valuestr(self, obj: rdf.RdfObject) -> str:
        ...


    def _field_header(path: Propertypath):
        return self.iri_shorthand
