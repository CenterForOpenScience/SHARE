# TODO: update
import pytest

from share.search.exceptions import IndexStrategyError
from share.search.index_strategy import (
    IndexStrategy,
    each_strategy,
    all_strategy_names,
    get_strategy,
    sharev2_elastic5,
    sharev2_elastic8,
    trove_indexcard_flats,
    trovesearch_denorm,
)


@pytest.fixture
def expected_strategy_classes():
    return {
        'sharev2_elastic5': sharev2_elastic5.Sharev2Elastic5IndexStrategy,
        'sharev2_elastic8': sharev2_elastic8.Sharev2Elastic8IndexStrategy,
        'trove_indexcard_flats': trove_indexcard_flats.TroveIndexcardFlatsIndexStrategy,
        'trovesearch_denorm': trovesearch_denorm.TrovesearchDenormIndexStrategy,
    }


class TestBaseIndexStrategy:
    def test_get_index_strategy(self, mock_elastic_clients, expected_strategy_classes):
        for strategy_name, expected_strategy_class in expected_strategy_classes.items():
            index_strategy = get_strategy(strategy_name)
            assert isinstance(index_strategy, expected_strategy_class)

    def test_all_index_strategies(self, mock_elastic_clients, expected_strategy_classes):
        all_strategys = tuple(each_strategy())
        assert len(all_strategys) == len(expected_strategy_classes)
        strategy_names = {index_strategy.strategy_name for index_strategy in all_strategys}
        assert strategy_names == set(expected_strategy_classes.keys())
        for index_strategy in all_strategys:
            strategy_class = expected_strategy_classes[index_strategy.strategy_name]
            assert isinstance(index_strategy, strategy_class)
            assert issubclass(index_strategy.SpecificIndex, IndexStrategy.SpecificIndex)
            assert index_strategy.SpecificIndex is not IndexStrategy.SpecificIndex

    @pytest.mark.django_db
    def test_get_by_request(self, mock_elastic_clients):
        for _strategy in each_strategy():
            good_requests = [
                _strategy.strategy_name,
                ''.join((_strategy.indexname_prefix, 'foo')),
            ]
            for good_request in good_requests:
                _got_strategy = get_strategy(good_request)
                assert isinstance(_got_strategy, IndexStrategy)
                assert _got_strategy == _strategy
        with pytest.raises(IndexStrategyError):
            get_strategy('bad-request')
