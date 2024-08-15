import unittest

from share.search.index_strategy.trovesearch_nesterly import TrovesearchNesterlyIndexStrategy
from . import _common_trovesearch_tests


@unittest.skip('wip')
class TestTrovesearchNesterly(_common_trovesearch_tests.CommonTrovesearchTests):
    # for RealElasticTestCase
    def get_index_strategy(self):
        return TrovesearchNesterlyIndexStrategy('test_trovesearch_nesterly')
