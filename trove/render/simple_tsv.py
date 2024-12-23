import csv

from trove.vocab import mediatypes

from .simple_csv import TrovesearchSimpleCsvRenderer


class TrovesearchSimpleTsvRenderer(TrovesearchSimpleCsvRenderer):
    MEDIATYPE = mediatypes.TSV
    CSV_DIALECT: type[csv.Dialect] = csv.excel_tab
