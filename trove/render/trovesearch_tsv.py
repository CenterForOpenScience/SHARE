import csv

from trove.vocab import mediatypes

from .trovesearch_csv import TrovesearchCsvRenderer


class TrovesearchTsvRenderer(TrovesearchCsvRenderer):
    MEDIATYPE = mediatypes.TSV
    CSV_DIALECT = csv.excel_tab
