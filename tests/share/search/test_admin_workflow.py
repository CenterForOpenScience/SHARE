from unittest import mock

from django.test.client import Client
import pytest

from share.models import ShareUser
from share.search import index_strategy


@pytest.mark.django_db
def test_admin_search_indexes_view(mock_elastic_clients):
    credentials = {'username': 'test-test-test', 'password': 'password-password'}
    ShareUser.objects.create_superuser(**credentials)
    client = Client()
    client.login(**credentials)
    with mock.patch('share.search.index_strategy.elastic8.elasticsearch8'):
        resp = client.get('/admin/search-indexes')
        for strategy_name in index_strategy.all_index_strategies():
            _index_strategy = index_strategy.get_index_strategy(strategy_name)
            expected_header = f'<h3 id="{_index_strategy.current_indexname}">current index: <i>{_index_strategy.current_indexname}</i></h3>'
            assert expected_header.encode() in resp.content
