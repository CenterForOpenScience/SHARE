from __future__ import annotations
from collections.abc import (
    Generator,
    Iterator,
    Sequence,
)
import csv
import dataclasses
import functools
import itertools
import logging
from typing import TYPE_CHECKING, ClassVar

from trove.trovesearch.search_params import (
    CardsearchParams,
    ValuesearchParams,
)
from trove.util.iter import iter_unique
from trove.util.json import json_prims
from trove.util.propertypath import Propertypath, GLOB_PATHSTEP
from trove.vocab import mediatypes
from trove.vocab import osfmap
from ._simple_trovesearch import SimpleTrovesearchRenderer
from .rendering import ProtoRendering
from .rendering.streamable import StreamableRendering
if TYPE_CHECKING:
    from trove.util.trove_params import BasicTroveParams
    from trove.util.json import (
        JsonObject,
        JsonPath,
    )

_logger = logging.getLogger(__name__)

type CsvValue = str | int | float | None

_MULTIVALUE_DELIMITER = ' ; '  # possible improvement: smarter in-value delimiting?
_VALUE_KEY_PREFERENCE = ('@value', '@id', 'name', 'prefLabel', 'label')
_ID_JSONPATH = ('@id',)


class TrovesearchSimpleCsvRenderer(SimpleTrovesearchRenderer):
    MEDIATYPE = mediatypes.CSV
    CSV_DIALECT: ClassVar[type[csv.Dialect]] = csv.excel

    def multicard_rendering(self, card_pages: Iterator[Sequence[tuple[str, JsonObject]]]) -> ProtoRendering:
        _doc = TabularDoc(
            card_pages,
            trove_params=getattr(self.response_focus, 'search_params', None),
        )
        return StreamableRendering(
            mediatype=self.MEDIATYPE,
            content_stream=csv_stream(self.CSV_DIALECT, _doc.header(), _doc.rows()),
        )


def csv_stream(
    csv_dialect: type[csv.Dialect],
    header: list[CsvValue],
    rows: Iterator[list[CsvValue]],
) -> Iterator[str]:
    _writer = csv.writer(_Echo(), dialect=csv_dialect)
    yield _writer.writerow(header)
    for _row in rows:
        yield _writer.writerow(_row)


@dataclasses.dataclass
class TabularDoc:
    card_pages: Iterator[Sequence[tuple[str, JsonObject]]]
    trove_params: BasicTroveParams | None = None
    _started: bool = False

    @functools.cached_property
    def column_jsonpaths(self) -> tuple[JsonPath, ...]:
        _column_jsonpaths = (
            _osfmap_jsonpath(_path)
            for _path in self._column_paths()
        )
        return (_ID_JSONPATH, *_column_jsonpaths)

    def _column_paths(self) -> Iterator[Propertypath]:
        _pathlists: list[Sequence[Propertypath]] = []
        if self.trove_params is not None:  # hacks
            if GLOB_PATHSTEP in self.trove_params.attrpaths_by_type:
                _pathlists.append(self.trove_params.attrpaths_by_type[GLOB_PATHSTEP])
            if isinstance(self.trove_params, ValuesearchParams):
                _expected_card_types = set(self.trove_params.valuesearch_type_iris())
            elif isinstance(self.trove_params, CardsearchParams):
                _expected_card_types = set(self.trove_params.cardsearch_type_iris())
            else:
                _expected_card_types = set()
            for _type_iri in sorted(_expected_card_types, key=len):
                try:
                    _pathlist = self.trove_params.attrpaths_by_type[_type_iri]
                except KeyError:
                    pass
                else:
                    _pathlists.append(_pathlist)
        if not _pathlists:
            _pathlists.append(osfmap.DEFAULT_TABULAR_SEARCH_COLUMN_PATHS)
        return iter_unique(itertools.chain.from_iterable(_pathlists))

    def header(self) -> list[CsvValue]:
        return ['.'.join(_path) for _path in self.column_jsonpaths]

    def rows(self) -> Generator[list[CsvValue]]:
        assert not self._started
        self._started = True
        for _page in self.card_pages:
            for _card_iri, _osfmap_json in _page:
                yield self._row_values(_osfmap_json)

    def _row_values(self, osfmap_json: JsonObject) -> list[CsvValue]:
        return [
            self._row_field_value(osfmap_json, _field_path)
            for _field_path in self.column_jsonpaths
        ]

    def _row_field_value(self, osfmap_json: JsonObject, field_path: JsonPath) -> CsvValue:
        _rendered_values = [
            _obj
            for _obj in json_prims(osfmap_json, field_path, _VALUE_KEY_PREFERENCE)
            if _obj is not None
        ]
        if len(_rendered_values) == 1:
            return _rendered_values[0]  # preserve type for single numbers
        # for multiple values, can only be a string
        return _MULTIVALUE_DELIMITER.join(map(str, _rendered_values))


def _osfmap_jsonpath(iri_path: Propertypath) -> JsonPath:
    _shorthand = osfmap.osfmap_json_shorthand()
    return tuple(
        _shorthand.compact_iri(_pathstep)
        for _pathstep in iri_path
    )


class _Echo:
    '''a write-only file-like object, to convince `csv.csvwriter.writerow` to return strings

    from https://docs.djangoproject.com/en/5.1/howto/outputting-csv/#streaming-large-csv-files
    '''
    def write(self, line: str) -> str:
        return line
