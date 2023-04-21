import pytest

from share.search.exceptions import IndexStrategyError
from share.search.index_strategy import (
    IndexStrategy,
    sharev2_elastic5,
    sharev2_elastic8,
)


@pytest.fixture
def expected_strategy_classes(fake_elastic_strategies):
    return {
        'my_es5_strategy': sharev2_elastic5.Sharev2Elastic5IndexStrategy,
        'my_es8_strategy': sharev2_elastic8.Sharev2Elastic8IndexStrategy,
        'another_es8_strategy': sharev2_elastic8.Sharev2Elastic8IndexStrategy,
    }


class TestBaseIndexStrategy:
    def test_get_by_name(self, mock_elastic_clients, expected_strategy_classes):
        for strategy_name, expected_strategy_class in expected_strategy_classes.items():
            index_strategy = IndexStrategy.get_by_name(strategy_name)
            assert isinstance(index_strategy, expected_strategy_class)

    def test_all_strategies(self, mock_elastic_clients, expected_strategy_classes):
        all_strategys = tuple(IndexStrategy.all_strategies())
        assert len(all_strategys) == len(expected_strategy_classes)
        strategy_names = {index_strategy.name for index_strategy in all_strategys}
        assert strategy_names == set(expected_strategy_classes.keys())
        for index_strategy in all_strategys:
            strategy_class = expected_strategy_classes[index_strategy.name]
            assert isinstance(index_strategy, strategy_class)
            assert issubclass(index_strategy.SpecificIndex, IndexStrategy.SpecificIndex)
            assert index_strategy.SpecificIndex is not IndexStrategy.SpecificIndex

    def test_get_by_specific_indexname(self, mock_elastic_clients, expected_strategy_classes, fake_elastic_strategies):
        for strategy_name, expected_strategy_class in expected_strategy_classes.items():
            indexname_prefix = IndexStrategy.get_by_name(strategy_name).indexname_prefix
            specific_indexname = ''.join((indexname_prefix, 'foo'))
            specific_index = IndexStrategy.get_specific_index(specific_indexname)
            assert isinstance(specific_index.index_strategy, expected_strategy_class)
            assert isinstance(specific_index, expected_strategy_class.SpecificIndex)
            assert specific_index.indexname == specific_indexname
            bad_indexname = 'foo_foo'  # assumed to not start with index prefix
            with pytest.raises(IndexStrategyError):
                IndexStrategy.get_specific_index(bad_indexname)

    def test_get_by_request(self, mock_elastic_clients, fake_elastic_strategies):
        for strategy_name in mock_elastic_clients.keys():
            index_strategy = IndexStrategy.get_by_name(strategy_name)
            good_requests = [
                strategy_name,
                index_strategy.current_indexname,
                ''.join((index_strategy.indexname_prefix, 'foo')),
            ]
            for good_request in good_requests:
                specific_index = IndexStrategy.get_for_searching(good_request)
                assert isinstance(specific_index, index_strategy.SpecificIndex)
                assert specific_index.index_strategy is index_strategy
                if good_request == strategy_name:
                    assert specific_index == index_strategy.pls_get_default_for_searching()
                else:
                    assert specific_index.indexname == good_request
            # bad calls:
            with pytest.raises(IndexStrategyError):
                IndexStrategy.get_for_searching('bad-request')
            with pytest.raises(ValueError):
                IndexStrategy.get_for_searching()
            with pytest.raises(ValueError):
                IndexStrategy.get_for_searching(requested_name=None)
