# TODO: update
import pytest

from share.search.exceptions import IndexStrategyError
from share.search.index_strategy import (
    IndexStrategy,
    each_strategy,
    get_strategy,
    sharev2_elastic8,
    trove_indexcard_flats,
    trovesearch_denorm,
    parse_strategy_name,
)
from share.search.index_strategy._indexnames import combine_indexname_parts
from tests.share.search import patch_index_strategies


@pytest.fixture
def patched_strategies(mock_elastic_clients):
    _strategies = [
        sharev2_elastic8.Sharev2Elastic8IndexStrategy('sharev2_elastic8'),
        trove_indexcard_flats.TroveIndexcardFlatsIndexStrategy('trove_indexcard_flats'),
        trovesearch_denorm.TrovesearchDenormIndexStrategy('trovesearch_denorm'),
    ]
    with patch_index_strategies(_strategies):
        yield _strategies


class TestBaseIndexStrategy:
    def test_get_index_strategy(self, patched_strategies):
        for expected_strategy in patched_strategies:
            gotten_strategy = get_strategy(expected_strategy.strategy_name)
            assert gotten_strategy == expected_strategy

    def test_all_index_strategies(self, patched_strategies):
        all_strategys = tuple(each_strategy())
        assert len(all_strategys) == len(patched_strategies)
        gotten_names = {index_strategy.strategy_name for index_strategy in all_strategys}
        assert gotten_names == {strategy.strategy_name for strategy in patched_strategies}
        for index_strategy in all_strategys:
            assert issubclass(index_strategy.SpecificIndex, IndexStrategy.SpecificIndex)
            assert index_strategy.SpecificIndex is not IndexStrategy.SpecificIndex

    @pytest.mark.django_db
    def test_get_by_request(self, patched_strategies):
        for _strategy in patched_strategies:
            good_requests = [
                _strategy.strategy_name,
                combine_indexname_parts(_strategy.strategy_name, _strategy.strategy_check),
                combine_indexname_parts(_strategy.strategy_name, _strategy.strategy_check, 'foo'),
            ]
            for good_request in good_requests:
                _got_strategy = parse_strategy_name(good_request)
                assert isinstance(_got_strategy, IndexStrategy)
                assert _got_strategy == _strategy
        with pytest.raises(IndexStrategyError):
            get_strategy('bad-request')
