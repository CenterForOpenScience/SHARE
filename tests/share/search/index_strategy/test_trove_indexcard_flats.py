import pytest

from share.search.index_strategy.trove_indexcard_flats import TroveIndexcardFlatsIndexStrategy

from . import _common_trovesearch_tests


@pytest.mark.skip
class TestTroveIndexcardFlats(_common_trovesearch_tests.CommonTrovesearchTests):
    # for RealElasticTestCase
    def get_index_strategy(self):
        return TroveIndexcardFlatsIndexStrategy('test_trove_indexcard_flats')

    def cardsearch_integer_cases(self):
        yield from ()  # integers not indexed by this strategy

    def cardsearch_trailingslash_cases(self):
        yield from ()  # trailing-slash handling improved in trovesearch_denorm

    def valuesearch_sameas_cases(self):
        yield from ()  # sameas handling improved in trovesearch_denorm

    def valuesearch_trailingslash_cases(self):
        yield from ()  # trailing-slash handling improved in trovesearch_denorm
