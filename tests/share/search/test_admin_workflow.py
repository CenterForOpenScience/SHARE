from unittest import mock

from django.test.client import Client
import pytest

from share.models import ShareUser
from share.search.index_strategy import IndexStrategy


@pytest.mark.django_db
def test_admin_search_indexes_view(fake_elastic_strategies, mock_elastic_clients):
    credentials = {'username': 'test-test-test', 'password': 'password-password'}
    ShareUser.objects.create_superuser(**credentials)
    client = Client()
    client.login(**credentials)
    with mock.patch('share.search.index_strategy.elastic8.elasticsearch8'):
        resp = client.get('/admin/search-indexes')
        for strategy_name in fake_elastic_strategies:
            index_strategy = IndexStrategy.get_by_name(strategy_name)
            expected_header = f'<h3>current index: <i>{index_strategy.current_indexname}</i></h3>'
            assert expected_header.encode() in resp.content
