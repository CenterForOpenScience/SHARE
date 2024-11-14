import csv

from trove.vocab import mediatypes

from .simple_tsv import TrovesearchSimpleTsvRenderer


class TrovesearchSimpleCsvRenderer(TrovesearchSimpleTsvRenderer):
    MEDIATYPE = mediatypes.COMMA_SEPARATED_VALUES
    _CSV_DIALECT = csv.excel
