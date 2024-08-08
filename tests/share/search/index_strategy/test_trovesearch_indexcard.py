import unittest

from share.search.index_strategy.trovesearch_indexcard import TrovesearchIndexcardIndexStrategy
from . import _common_trovesearch_tests


#@unittest.skip('wip')
class TestTrovesearchIndexcard(_common_trovesearch_tests.CommonTrovesearchTests):
    # for RealElasticTestCase
    def get_index_strategy(self):
        return TrovesearchIndexcardIndexStrategy('test_trovesearch_indexcard')

    # override CommonTrovesearchTests
    def valuesearch_complex_cases(self):
        yield from ()  # "complex" valuesearches are the ones this indexcard strategy can't handle
