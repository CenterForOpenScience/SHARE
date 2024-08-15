import unittest

from share.search.index_strategy.trovesearch_flattery import TrovesearchFlatteryIndexStrategy
from . import _common_trovesearch_tests


@unittest.skip('wip')
class TestTrovesearchFlattery(_common_trovesearch_tests.CommonTrovesearchTests):
    # for RealElasticTestCase
    def get_index_strategy(self):
        return TrovesearchFlatteryIndexStrategy('test_trovesearch_flattery')

    # override CommonTrovesearchTests
    def valuesearch_complex_cases(self):
        yield from ()  # "complex" valuesearches are the ones this flattery strategy can't handle
