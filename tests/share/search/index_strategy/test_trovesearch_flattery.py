from . import _common_trovesearch_tests


class TestTrovesearchFlattery(_common_trovesearch_tests.CommonTrovesearchTests):
    strategy_name_for_real = 'trovesearch_flattery'
    strategy_name_for_test = 'test_trovesearch_flattery'
