# TODO: update
import pytest

from share.search.exceptions import IndexStrategyError
from share.search.index_strategy import (
    all_index_strategies,
    get_index_strategy,
    get_specific_index,
    get_index_for_sharev2_search,
    IndexStrategy,
    sharev2_elastic5,
    sharev2_elastic8,
    trove_indexcard_flats,
)


@pytest.fixture
def expected_strategy_classes():
    return {
        'sharev2_elastic5': sharev2_elastic5.Sharev2Elastic5IndexStrategy,
        'sharev2_elastic8': sharev2_elastic8.Sharev2Elastic8IndexStrategy,
        'trove_indexcard_flats': trove_indexcard_flats.TroveIndexcardFlatsIndexStrategy,
    }


class TestBaseIndexStrategy:
    def test_get_index_strategy(self, mock_elastic_clients, expected_strategy_classes):
        for strategy_name, expected_strategy_class in expected_strategy_classes.items():
            index_strategy = get_index_strategy(strategy_name)
            assert isinstance(index_strategy, expected_strategy_class)

    def test_all_index_strategies(self, mock_elastic_clients, expected_strategy_classes):
        all_strategys = tuple(all_index_strategies().values())
        assert len(all_strategys) == len(expected_strategy_classes)
        strategy_names = {index_strategy.name for index_strategy in all_strategys}
        assert strategy_names == set(expected_strategy_classes.keys())
        for index_strategy in all_strategys:
            strategy_class = expected_strategy_classes[index_strategy.name]
            assert isinstance(index_strategy, strategy_class)
            assert issubclass(index_strategy.SpecificIndex, IndexStrategy.SpecificIndex)
            assert index_strategy.SpecificIndex is not IndexStrategy.SpecificIndex

    def test_get_by_specific_indexname(self, mock_elastic_clients, expected_strategy_classes):
        for strategy_name, expected_strategy_class in expected_strategy_classes.items():
            indexname_prefix = get_index_strategy(strategy_name).indexname_prefix
            specific_indexname = ''.join((indexname_prefix, 'foo'))
            specific_index = get_specific_index(specific_indexname)
            assert isinstance(specific_index.index_strategy, expected_strategy_class)
            assert isinstance(specific_index, expected_strategy_class.SpecificIndex)
            assert specific_index.indexname == specific_indexname
            bad_indexname = 'foo_foo'  # assumed to not start with index prefix
            with pytest.raises(IndexStrategyError):
                get_specific_index(bad_indexname)

    @pytest.mark.django_db
    def test_get_by_request(self, mock_elastic_clients):
        for strategy_name, index_strategy in all_index_strategies().items():
            good_requests = [
                strategy_name,
                index_strategy.current_indexname,
                ''.join((index_strategy.indexname_prefix, 'foo')),
            ]
            for good_request in good_requests:
                specific_index = get_index_for_sharev2_search(good_request)
                assert isinstance(specific_index, index_strategy.SpecificIndex)
                assert specific_index.index_strategy is index_strategy
        with pytest.raises(IndexStrategyError):
            get_index_for_sharev2_search('bad-request')
