from unittest import mock

import pytest

from share.search.exceptions import IndexStrategyError
from share.search.index_strategy import (
    IndexStrategy,
    sharev2_elastic5,
    sharev2_elastic8,
)


@pytest.fixture
def fake_elastic_settings(settings):
    settings.ELASTICSEARCH = {
        **settings.ELASTICSEARCH,
        'INDEX_STRATEGIES': {
            'my_es5_strategy': {
                'CLUSTER_SETTINGS': {'URL': 'blah'},
                'INDEX_STRATEGY_CLASS': 'share.search.index_strategy.sharev2_elastic5.Sharev2Elastic5IndexStrategy',
            },
            'my_es8_strategy': {
                'CLUSTER_SETTINGS': {'URL': 'bleh'},
                'INDEX_STRATEGY_CLASS': 'share.search.index_strategy.sharev2_elastic8.Sharev2Elastic8IndexStrategy',
            },
            'another_es8_strategy': {
                'CLUSTER_SETTINGS': {'URL': 'bluh'},
                'INDEX_STRATEGY_CLASS': 'share.search.index_strategy.sharev2_elastic8.Sharev2Elastic8IndexStrategy',
            },
        },
    }


@pytest.fixture
def expected_strategy_classes(fake_elastic_settings):
    return {
        'my_es5_strategy': sharev2_elastic5.Sharev2Elastic5IndexStrategy,
        'my_es8_strategy': sharev2_elastic8.Sharev2Elastic8IndexStrategy,
        'another_es8_strategy': sharev2_elastic8.Sharev2Elastic8IndexStrategy,
    }


@pytest.fixture
def mock_es_clients(fake_elastic_settings):
    with mock.patch('share.search.index_strategy.sharev2_elastic5.elasticsearch5') as es5_mockpackage:
        with mock.patch('share.search.index_strategy.elastic8.elasticsearch8') as es8_mockpackage:
            es5_mockclient = es5_mockpackage.Elasticsearch.return_value
            es8_mockclient = es8_mockpackage.Elasticsearch.return_value
            yield {
                'my_es5_strategy': es5_mockclient,
                'my_es8_strategy': es8_mockclient,
                'another_es8_strategy': es8_mockclient,
            }


class TestBaseIndexStrategy:
    def test_get_by_name(self, mock_es_clients, expected_strategy_classes):
        for strategy_name, expected_strategy_class in expected_strategy_classes.items():
            index_strategy = IndexStrategy.get_by_name(strategy_name)
            assert isinstance(index_strategy, expected_strategy_class)

    def test_all_strategies(self, mock_es_clients, expected_strategy_classes):
        all_strategys = tuple(IndexStrategy.all_strategies())
        assert len(all_strategys) == len(expected_strategy_classes)
        strategy_names = {index_strategy.name for index_strategy in all_strategys}
        assert strategy_names == set(expected_strategy_classes.keys())
        for index_strategy in all_strategys:
            strategy_class = expected_strategy_classes[index_strategy.name]
            assert isinstance(index_strategy, strategy_class)
            assert issubclass(index_strategy.SpecificIndex, IndexStrategy.SpecificIndex)
            assert index_strategy.SpecificIndex is not IndexStrategy.SpecificIndex

    def test_get_by_specific_indexname(self, mock_es_clients, expected_strategy_classes, fake_elastic_settings):
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

    def test_get_by_request(self, mock_es_clients, fake_elastic_settings):
        for strategy_name in mock_es_clients.keys():
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

    # def test_stream_actions(self, mock_es_clients):
    #     input_actions = [
    #         {'index': {'foo': 0}},
    #         {'delete': {'bar': 1}},
    #     ]
    #     response_stream = [
    #         (True, {'index': {'foo': 0}}),
    #         (True, {'delete': {'bar': 1}}),
    #     ]
    #     expected_return = [
    #         (True, 'index', {'foo': 0}),
    #         (True, 'delete', {'bar': 1}),
    #     ]
    #     with patch(
    #             'share.search.elastic_manager.elastic_helpers.bulk',
    #             return_value=response_stream,
    #     ) as mock_streaming_bulk:
    #         actual_return = list(isolated_elastic_manager.stream_actions(input_actions))

    #         mock_streaming_bulk.assert_called_once_with(
    #             isolated_elastic_manager.es_client,
    #             input_actions,
    #             max_chunk_bytes=isolated_elastic_manager.MAX_CHUNK_BYTES,
    #             raise_on_error=False,
    #         )
    #         assert actual_return == expected_return

    # def test_send_actions_sync(self, mock_es_clients):
    #     input_actions = [
    #         {'index': {'foo': 0}},
    #         {'delete': {'bar': 1}},
    #     ]
    #     with patch('share.search.elastic_manager.elastic_helpers.bulk') as bock_mulk:
    #         isolated_elastic_manager.send_actions_sync(input_actions)
    #         bock_mulk.assert_called_once_with(isolated_elastic_manager.es_client, input_actions)

    # @pytest.mark.parametrize('index_names, expected_arg', [
    #     (['trove_index'], 'trove_index'),
    #     (['postrend_index'], 'postrend_index'),
    #     (['trove_index', 'postrend_index'], 'trove_index,postrend_index'),
    # ])
    # def test_refresh_indexes(self, mock_es_clients, index_names, expected_arg):
    #     mock_es_client = isolated_elastic_manager.es_client

    #     isolated_elastic_manager.refresh_indexes(index_names)

    #     mock_es_client.indices.refresh.assert_called_once_with(index=expected_arg)

    # @pytest.mark.parametrize('index_name', [
    #     'postrend_index',
    #     'trove_index',
    # ])
    # def test_initial_update_primary_alias(self, mock_es_clients, index_name, settings):
    #     alias_name = settings.ELASTICSEARCH['PRIMARY_INDEX']
    #     mock_es_client = isolated_elastic_manager.es_client
    #     mock_es_client.configure_mock(**{
    #         'indices.get_alias.side_effect': NotFoundError,
    #     })

    #     isolated_elastic_manager.update_primary_alias(index_name)

    #     mock_es_client.indices.get_alias.assert_called_once_with(name=alias_name)
    #     mock_es_client.indices.update_aliases.assert_called_once_with(
    #         body={'actions': [
    #             {'add': {'index': index_name, 'alias': alias_name}}
    #         ]}
    #     )

    # @pytest.mark.parametrize('index_name', [
    #     'postrend_index',
    #     'trove_index',
    # ])
    # def test_update_primary_alias(self, mock_es_clients, index_name, settings):
    #     alias_name = settings.ELASTICSEARCH['PRIMARY_INDEX']
    #     mock_es_client = isolated_elastic_manager.es_client
    #     mock_es_client.configure_mock(**{
    #         'indices.get_alias.return_value': {
    #             'old_primary': {'alias': alias_name},
    #         },
    #     })

    #     isolated_elastic_manager.update_primary_alias(index_name)

    #     mock_es_client.indices.get_alias.assert_called_once_with(name=alias_name)
    #     mock_es_client.indices.update_aliases.assert_called_once_with(
    #         body={'actions': [
    #             {'remove': {'index': 'old_primary', 'alias': alias_name}},
    #             {'add': {'index': index_name, 'alias': alias_name}},
    #         ]}
    #     )

    # @pytest.mark.parametrize('index_name', [
    #     'postrend_index',
    #     'trove_index',
    # ])
    # def test_unnecessary_update_primary_alias(self, mock_es_clients, index_name, settings):
    #     alias_name = settings.ELASTICSEARCH['PRIMARY_INDEX']
    #     mock_es_client = isolated_elastic_manager.es_client
    #     mock_es_client.configure_mock(**{
    #         'indices.get_alias.return_value': {
    #             index_name: {'alias': alias_name},
    #         },
    #     })

    #     isolated_elastic_manager.update_primary_alias(index_name)

    #     mock_es_client.indices.get_alias.assert_called_once_with(name=alias_name)
    #     mock_es_client.indices.update_aliases.assert_not_called()
