from unittest import mock

import pytest

from share.search.index_strategy.elastic8 import Elastic8IndexStrategy
from share.search import messages
from share.util.checksum_iri import ChecksumIri


FAKE_ACTION_ITERATOR = object()


class FakeElastic8IndexStrategy(Elastic8IndexStrategy):
    CURRENT_STRATEGY_CHECKSUM = ChecksumIri(
        checksumalgorithm_name='sha-256',
        salt='FakeElastic8IndexStrategy',
        hexdigest='5371df2d0e3daaa9f1c344d14384cdbe65000f2b449b1c2f30ae322b0321eb12',
    )

    @property
    def supported_message_types(self):
        return {
            messages.MessageType.INDEX_SUID,
            messages.MessageType.BACKFILL_SUID,
        }

    @property
    def backfill_message_type(self):
        return messages.MessageType.BACKFILL_SUID

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
    def fake_strategy(self, mock_es_client, settings):
        settings.ELASTICSEARCH8_URL = 'http://nowhere.example:12345/'
        strat = FakeElastic8IndexStrategy(name='fake_es8')
        strat.assert_strategy_is_current()
        return strat

    @pytest.fixture
    def fake_specific_index(self, fake_strategy):
        return fake_strategy.for_current_index()

    def test_pls_create(self, fake_specific_index, mock_es_client):
        mock_es_client.indices.exists.return_value = False
        fake_specific_index.pls_create()
        mock_es_client.indices.exists.assert_called_once_with(
            index=fake_specific_index.indexname,
        )
        mock_es_client.indices.create.assert_called_once_with(
            index=fake_specific_index.indexname,
            settings=fake_specific_index.index_strategy.index_settings(),
            mappings=fake_specific_index.index_strategy.index_mappings(),
        )
        # already exists:
        mock_es_client.reset_mock()
        mock_es_client.indices.exists.return_value = True,
        fake_specific_index.pls_create()
        mock_es_client.indices.exists.assert_called_once_with(
            index=fake_specific_index.indexname,
        )
        mock_es_client.indices.create.assert_not_called()

    def test_delete_index(self, fake_specific_index, mock_es_client):
        fake_specific_index.pls_delete()
        mock_es_client.indices.delete.assert_called_once_with(
            index=fake_specific_index.indexname,
            ignore=[400, 404],
        )
