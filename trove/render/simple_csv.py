import csv

from trove.vocab import mediatypes

from .simple_tsv import TrovesearchSimpleTsvRenderer


class TrovesearchSimpleCsvRenderer(TrovesearchSimpleTsvRenderer):
    MEDIATYPE = mediatypes.CSV
    CSV_DIALECT = csv.excel
