from unittest import mock

import pytest

from share.search.index_strategy import (
    IndexStrategy,
    Elastic8IndexStrategy,
    # TroveV0IndexStrategy,
)


FAKE_ACTION_ITERATOR = object()


class FakeElastic8IndexStrategy(Elastic8IndexStrategy):
    def index_settings(self):
        return {'my-settings': 'lol'}

    def index_mappings(self):
        return {'my-mappings': 'lol'}

    def build_elastic_actions(self, messages_chunk):
        return FAKE_ACTION_ITERATOR


class TestIndexStrategy:
    @pytest.fixture
    def mock_es_client(self):
        with mock.patch('share.search.index_strategy.elastic8.elasticsearch8') as es8_mockpackage:
            es8_mockclient = es8_mockpackage.Elasticsearch.return_value
            yield es8_mockclient

    @pytest.fixture
    def fake_strategy(self):
        return FakeElastic8IndexStrategy(
            name='fake_es8',
            cluster_url='http://nowhere.example/',
        )

    def test_elastic8_index_strategy(self, fake_strategy, mock_es_client):
        mock_es_client.configure_mock(**{
            'indices.exists.return_value': False,
        })
        fake_strategy.pls_create()
        mock_es_client.indices.create.assert_called_once_with(
            fake_strategy.current_index_name,
            body={
                'settings': fake_strategy.index_settings(),
                'mappings': fake_strategy.index_mappings(),
            },
        )

    def test_create_index_already_exists(self, fake_strategy, mock_es_client):
        mock_es_client.configure_mock(**{
            'indices.exists.return_value': True,
        })
        fake_strategy.pls_create(fake_strategy.current_index_name)
        mock_es_client.indices.create.assert_not_called()

    def test_delete_index(self, fake_strategy, mock_es_client):
        fake_strategy.pls_delete()
        mock_es_client.indices.delete.assert_called_once_with(
            index=fake_strategy.current_index_name,
            ignore=[400, 404],
        )

    def test_pls_setup_as_needed(self, fake_strategy, mock_es_client):
        fake_strategy.pls_setup_as_needed()

    def test_pls_handle_messages_chunk(self, fake_strategy, mock_es_client):
        fake_strategy.pls_handle_messages_chunk(messages_chunk)

    def test_pls_organize_fill(self, fake_strategy, mock_es_client):
        fake_strategy.pls_organize_fill()

    # def test_stream_actions(self, mock_es_client):
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

    # def test_send_actions_sync(self, mock_es_client):
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
    # def test_refresh_indexes(self, mock_es_client, index_names, expected_arg):
    #     mock_es_client = isolated_elastic_manager.es_client

    #     isolated_elastic_manager.refresh_indexes(index_names)

    #     mock_es_client.indices.refresh.assert_called_once_with(index=expected_arg)

    # @pytest.mark.parametrize('index_name', [
    #     'postrend_index',
    #     'trove_index',
    # ])
    # def test_initial_update_primary_alias(self, mock_es_client, index_name, settings):
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
    # def test_update_primary_alias(self, mock_es_client, index_name, settings):
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
    # def test_unnecessary_update_primary_alias(self, mock_es_client, index_name, settings):
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

