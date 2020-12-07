from unittest.mock import patch, call

import pytest

from share.search.elastic_manager import ElasticManager
from share.search.index_setup import ShareClassicIndexSetup, PostRendBackcompatIndexSetup


class TestIsolatedElasticManager:
    @pytest.fixture
    def isolated_elastic_manager(self, settings):
        custom_settings = {
            **settings.ELASTICSEARCH,
            'INDEXES': {
                'classic_index': {
                    'INDEX_SETUP': 'share_classic',
                },
                'postrend_index': {
                    'INDEX_SETUP': 'postrend_backcompat',
                },
            },
        }

        isolated_elastic_manager = ElasticManager(custom_settings)
        with patch.object(isolated_elastic_manager, 'es_client'):
            yield isolated_elastic_manager

    @pytest.mark.parametrize('index_name, expected_setup_class', [
        ('classic_index', ShareClassicIndexSetup),
        ('postrend_index', PostRendBackcompatIndexSetup),
    ])
    def test_get_index_setup(self, isolated_elastic_manager, index_name, expected_setup_class):
        index_setup = isolated_elastic_manager.get_index_setup(index_name)
        assert isinstance(index_setup, expected_setup_class)

    @pytest.mark.parametrize('index_name', [
        'classic_index',
        'postrend_index',
    ])
    def test_create_index(self, isolated_elastic_manager, index_name):
        index_setup = isolated_elastic_manager.get_index_setup(index_name)
        mock_es_client = isolated_elastic_manager.es_client

        isolated_elastic_manager.create_index(index_name)

        mock_es_client.indices.create.assert_called_once_with(index_name, ignore=400)
        mock_es_client.indices.put_settings.assert_called_once_with(
            index=index_name,
            body=index_setup.index_settings,
        )
        mock_es_client.indices.put_mapping.assert_has_calls([
            call(
                doc_type=doc_type,
                body={doc_type: mapping},
                index=index_name,
            ) for doc_type, mapping in index_setup.index_mappings.items()
        ], any_order=True)

    @pytest.mark.parametrize('index_name', [
        'classic_index',
        'postrend_index',
    ])
    def test_delete_index(self, isolated_elastic_manager, index_name):
        mock_es_client = isolated_elastic_manager.es_client

        isolated_elastic_manager.delete_index(index_name)

        mock_es_client.indices.delete.assert_called_once_with(index=index_name, ignore=[400, 404])

    def test_stream_actions(self, isolated_elastic_manager):
        input_actions = [
            {'index': {'foo': 0}},
            {'delete': {'bar': 1}},
        ]
        response_stream = [
            (True, {'index': {'foo': 0}}),
            (True, {'delete': {'bar': 1}}),
        ]
        expected_return = [
            (True, 'index', {'foo': 0}),
            (True, 'delete', {'bar': 1}),
        ]
        with patch(
                'share.search.elastic_manager.elastic_helpers.streaming_bulk',
                return_value=response_stream,
        ) as mock_streaming_bulk:
            actual_return = list(isolated_elastic_manager.stream_actions(input_actions))

            mock_streaming_bulk.assert_called_once_with(
                isolated_elastic_manager.es_client,
                input_actions,
                max_chunk_bytes=isolated_elastic_manager.MAX_CHUNK_BYTES,
                raise_on_error=False,
            )
            assert actual_return == expected_return

    def test_send_actions_sync(self, isolated_elastic_manager):
        input_actions = [
            {'index': {'foo': 0}},
            {'delete': {'bar': 1}},
        ]
        with patch('share.search.elastic_manager.elastic_helpers.bulk') as bock_mulk:
            isolated_elastic_manager.send_actions_sync(input_actions)
            bock_mulk.assert_called_once_with(isolated_elastic_manager.es_client, input_actions)

    @pytest.mark.parametrize('index_names, expected_arg', [
        (['classic_index'], 'classic_index'),
        (['postrend_index'], 'postrend_index'),
        (['classic_index', 'postrend_index'], 'classic_index,postrend_index'),
    ])
    def test_refresh_indexes(self, isolated_elastic_manager, index_names, expected_arg):
        mock_es_client = isolated_elastic_manager.es_client

        isolated_elastic_manager.refresh_indexes(index_names)

        mock_es_client.indices.refresh.assert_called_once_with(index=expected_arg)
