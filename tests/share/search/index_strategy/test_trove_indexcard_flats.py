from . import _common_trovesearch_tests


class TestTroveIndexcardFlats(_common_trovesearch_tests.CommonTrovesearchTests):
    strategy_name_for_real = 'trove_indexcard_flats'
    strategy_name_for_test = 'test_trove_indexcard_flats'
