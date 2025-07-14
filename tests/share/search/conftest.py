from unittest import mock

import pytest


@pytest.fixture
def mock_elastic_clients(settings):
    # set elastic urls to non-empty but non-usable values
    settings.ELASTICSEARCH8_URL = 'fake://bluh'
    with mock.patch('share.search.index_strategy.elastic8.elasticsearch8'):
        yield
    from share.search.index_strategy.elastic8 import Elastic8IndexStrategy
    Elastic8IndexStrategy._get_elastic8_client.cache_clear()
