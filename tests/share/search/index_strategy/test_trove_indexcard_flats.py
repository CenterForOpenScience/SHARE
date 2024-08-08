from share.search.index_strategy.trove_indexcard_flats import TroveIndexcardFlatsIndexStrategy

from . import _common_trovesearch_tests


class TestTroveIndexcardFlats(_common_trovesearch_tests.CommonTrovesearchTests):
    # for RealElasticTestCase
    def get_index_strategy(self):
        return TroveIndexcardFlatsIndexStrategy('test_trove_indexcard_flats')
