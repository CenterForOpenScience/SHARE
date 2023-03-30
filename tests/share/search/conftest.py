import pytest

from share.search.index_strategy import IndexStrategy


@pytest.fixture(scope='session')
def elastic_test_index_name():
    return 'test_share'


@pytest.fixture(params=['es5', 'es8'])
def elastic_test_cluster_url(request, settings):
    if request.param == 'es5':
        return settings.ELASTICSEARCH5_URL
    if request.param == 'es8':
        return settings.ELASTICSEARCH8_URL
    raise ValueError(request.param)


@pytest.fixture()
def actual_elasticsearch(elastic_test_index_name, elastic_test_cluster_url, settings):
    old_elasticsearch_settings = settings.ELASTICSEARCH
    settings.ELASTICSEARCH = {
        **old_elasticsearch_settings,
        'TIMEOUT': 5,
        'PRIMARY_INDEX': elastic_test_index_name,
        'LEGACY_INDEX': elastic_test_index_name,
        'BACKCOMPAT_INDEX': elastic_test_index_name,
        'ACTIVE_INDEXES': [elastic_test_index_name],
        'INDEX_STRATEGIES': {
            elastic_test_index_name: {
                'INDEX_STRATEGY_CLASS': 'share.search.index_strategy.sharev2_elastic5.Sharev2Elastic5IndexStrategy',
                'CLUSTER_SETTINGS': {
                    'URL': settings.ELASTICSEARCH5_URL,
                },
            },
        },
    }
    index_strategy = IndexStrategy.get_by_name(elastic_test_index_name)
    try:
        index_strategy.pls_delete()
        index_strategy.pls_setup()
        try:
            yield
        finally:
            index_strategy.pls_delete()
    except Exception as error:
        raise pytest.skip(f'Elasticsearch unavailable? (error: {error})')
