from . import _common_trovesearch_tests


class TestTrovesearchNesterly(_common_trovesearch_tests.CommonTrovesearchTests):
    strategy_name_for_real = 'trovesearch_nesterly'
    strategy_name_for_test = 'test_trovesearch_nesterly'
