from share.search.index_strategy.trovesearch_denorm import TrovesearchDenormIndexStrategy
from . import _common


class TestOsfsearchOnTrovesearchDenorm(_common.End2EndSearchTestCase):
    def get_index_strategy(self):  # for RealElasticTestCase
        return TrovesearchDenormIndexStrategy('test_osfsearch_on_trovesearch_denorm')
