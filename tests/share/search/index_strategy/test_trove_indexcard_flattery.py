from . import _common_trovesearch_tests


class TestTroveIndexcardFlattery(_common_trovesearch_tests.CommonTrovesearchTests):
    strategy_name_for_real = 'trove_indexcard_flattery'
    strategy_name_for_test = 'test_trove_indexcard_flattery'
