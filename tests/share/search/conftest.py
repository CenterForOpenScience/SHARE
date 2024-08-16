from unittest import mock

import pytest


@pytest.fixture
def mock_elastic_clients(settings):
    # set elastic urls to non-empty but non-usable values
    settings.ELASTICSEARCH5_URL = 'fake://bleh'
    settings.ELASTICSEARCH8_URL = 'fake://bluh'
    with mock.patch('share.search.index_strategy.sharev2_elastic5.elasticsearch5'):
        with mock.patch('share.search.index_strategy.elastic8.elasticsearch8'):
            yield
