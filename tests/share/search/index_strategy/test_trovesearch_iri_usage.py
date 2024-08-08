import unittest

from share.search.index_strategy.trovesearch_excessive import TrovesearchExcessiveIndexStrategy
from . import _common_trovesearch_tests


#@unittest.skip('wip')
class TestTrovesearchExcessive(_common_trovesearch_tests.CommonTrovesearchTests):
    # for RealElasticTestCase
    def get_index_strategy(self):
        return TrovesearchExcessiveIndexStrategy('test_trovesearch_excessive')

