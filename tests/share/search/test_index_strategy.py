from unittest.mock import patch, call

import pytest
from elasticsearch.exceptions import NotFoundError

from share.search.index_strategy import (
    IndexStrategy,
    Sharev2Elastic5IndexStrategy,
    Sharev2Elastic8IndexStrategy,
    TroveV0IndexStrategy,
)


class TestIndexStrategy:
    @pytest.fixture
    def mock_es_clients(self, settings):
        settings.ELASTICSEARCH = {
            **settings.ELASTICSEARCH,
            'INDEXES': {
                'my_es5_index': {
                    'CLUSTER_URL': 'blah',
                    'INDEX_STRATEGY_CLASS': 'share.search.index_strategy.sharev2_elastic5:Sharev2Elastic5IndexStrategy',
                },
                'my_es8_index': {
                    'CLUSTER_URL': 'bleh',
                    'INDEX_STRATEGY_CLASS': 'share.search.index_strategy.sharev2_elastic8:Sharev2Elastic8IndexStrategy',
                },
            },
        }
        es5_indexstrategy = IndexStrategy.by_name('my_es5_index')
        es8_indexstrategy = IndexStrategy.by_name('my_es8_index')
        with patch.object(es5_indexstrategy, 'es5_client') as es5_mockclient:
            with patch.object(es8_indexstrategy, 'es8_client') as es8_mockclient:
                yield {
                    'my_es5_index': es5_mockclient,
                    'my_es8_index': es8_mockclient,
                }

    @pytest.mark.parametrize('index_name, expected_setup_class', [
        ('my_es5_index', Sharev2Elastic5IndexStrategy),
        ('my_es8_index', Sharev2Elastic8IndexStrategy),
    ])
    def test_get_by_name(self, mock_es_clients, index_name, expected_setup_class):
        index_strategy = IndexStrategy.by_name(index_name)
        assert isinstance(index_strategy, expected_setup_class)

    def test_get_all_indexes(self, mock_es_clients):
        all_indexes = IndexStrategy.all_indexes()
        assert isinstance(all_indexes, tuple)
        assert len(all_indexes) == 2
        index_names = {
            index_strategy.name
            for index_strategy in all_indexes
        }
        assert index_names == {'my_es5_index', 'my_es8_index'}
        assert isinstance(all_indexes['my_es5_index'], Sharev2Elastic5IndexStrategy)
        assert isinstance(all_indexes['my_es8_index'], Sharev2Elastic8IndexStrategy)

    def test_create_index(self, mock_es_clients):
        for index_name, mock_es_client in mock_es_clients.items():
            index_strategy = IndexStrategy.by_name(index_name)
            mock_es_client.configure_mock(**{
                'indices.exists.return_value': False,
            })
            index_strategy.pls_create()
            mock_es_client.indices.create.assert_called_once_with(
                index_name,
                body={'settings': index_strategy.index_settings()},
            )
            mock_es_client.indices.put_mapping.assert_has_calls([
                call(
                    doc_type=doc_type,
                    body={doc_type: mapping},
                    index=index_name,
                ) for doc_type, mapping in index_strategy.index_mappings().items()
            ], any_order=True)

    def test_create_index_already_exists(self, mock_es_clients):
        for index_name, mock_es_client in mock_es_clients.items():
            index_strategy = IndexStrategy.by_name(index_name)
            mock_es_client.configure_mock(**{
                'indices.exists.return_value': True,
            })
            with pytest.raises(ValueError):
                index_strategy.pls_create(index_name)

    def test_delete_index(self, mock_es_clients):
        for index_name, mock_es_client in mock_es_clients.items():
            index_strategy = IndexStrategy.by_name(index_name)
            index_strategy.pls_delete()
            mock_es_client.indices.delete.assert_called_once_with(index=index_name, ignore=[400, 404])

    def test_exists_as_expected(self, mock_es_clients):
        for index_name, mock_es_client in mock_es_clients.keys():
            index_strategy = IndexStrategy.by_name(index_name)

    def test_pls_setup_as_needed(self, mock_es_clients):
        for index_name, mock_es_client in mock_es_clients.keys():
            index_strategy = IndexStrategy.by_name(index_name)

    def test_pls_handle_messages(self, mock_es_clients):
        for index_name, mock_es_client in mock_es_clients.keys():
            index_strategy = IndexStrategy.by_name(index_name)

    def test_pls_organize_redo(self, mock_es_clients):
        for index_name, mock_es_client in mock_es_clients.keys():
            index_strategy = IndexStrategy.by_name(index_name)

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
