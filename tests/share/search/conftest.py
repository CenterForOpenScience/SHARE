from unittest import mock

import pytest


@pytest.fixture
def fake_elastic_strategies(settings):
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
    return tuple(settings.ELASTICSEARCH['INDEX_STRATEGIES'].keys())


@pytest.fixture
def mock_elastic_clients(fake_elastic_strategies):
    with mock.patch('share.search.index_strategy.sharev2_elastic5.elasticsearch5') as es5_mockpackage:
        with mock.patch('share.search.index_strategy.elastic8.elasticsearch8') as es8_mockpackage:
            es5_mockclient = es5_mockpackage.Elasticsearch.return_value
            es8_mockclient = es8_mockpackage.Elasticsearch.return_value
            yield {
                'my_es5_strategy': es5_mockclient,
                'my_es8_strategy': es8_mockclient,
                'another_es8_strategy': es8_mockclient,
            }
