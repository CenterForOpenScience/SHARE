import functools
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

    @classmethod
    def define_current_indexes(cls):
        return {
            '': cls.IndexDefinition(
                mappings={'my-mappings': 'lol'},
                settings={'my-settings': 'lol'},
            ),
        }

    @functools.cached_property
    def es8_client(self):
        return mock.Mock()

    @property
    def supported_message_types(self):
        return {
            messages.MessageType.INDEX_SUID,
            messages.MessageType.BACKFILL_SUID,
        }

    @property
    def backfill_message_type(self):
        return messages.MessageType.BACKFILL_SUID

    def build_elastic_actions(self, messages_chunk):
        return FAKE_ACTION_ITERATOR


class TestIndexStrategy:
    @pytest.fixture
    def fake_strategy(self, settings):
        settings.ELASTICSEARCH8_URL = 'http://nowhere.example:12345/'
        strat = FakeElastic8IndexStrategy('fake_es8')
        strat.assert_strategy_is_current()
        return strat

    @pytest.fixture
    def fake_specific_index(self, fake_strategy):
        return fake_strategy.get_index('')

    @pytest.fixture
    def mock_es_client(self, fake_strategy):
        return fake_strategy.es8_client

    def test_pls_create(self, fake_specific_index, mock_es_client):
        mock_es_client.indices.exists.return_value = False
        fake_specific_index.pls_create()
        mock_es_client.indices.exists.assert_called_once_with(
            index=fake_specific_index.full_index_name,
        )
        mock_es_client.indices.create.assert_called_once_with(
            index=fake_specific_index.full_index_name,
            mappings={'my-mappings': 'lol'},
            settings={'my-settings': 'lol'},
        )
        # already exists:
        mock_es_client.reset_mock()
        mock_es_client.indices.exists.return_value = True,
        fake_specific_index.pls_create()
        mock_es_client.indices.exists.assert_called_once_with(
            index=fake_specific_index.full_index_name,
        )
        mock_es_client.indices.create.assert_not_called()

    def test_delete_index(self, fake_specific_index, mock_es_client):
        fake_specific_index.pls_delete()
        mock_es_client.indices.delete.assert_called_once_with(
            index=fake_specific_index.full_index_name,
            ignore=[400, 404],
        )
