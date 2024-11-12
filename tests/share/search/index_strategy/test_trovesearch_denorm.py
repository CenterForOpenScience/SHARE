from share.search.index_strategy.trovesearch_denorm import TrovesearchDenormIndexStrategy

from . import _common_trovesearch_tests


class TestTroveIndexcardFlats(_common_trovesearch_tests.CommonTrovesearchTests):
    # for RealElasticTestCase
    def get_index_strategy(self):
        return TrovesearchDenormIndexStrategy('test_trovesearch_denorm')
