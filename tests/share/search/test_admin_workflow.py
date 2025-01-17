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
    resp = client.get('/admin/search-indexes')
    for strategy_name in index_strategy.all_strategy_names():
        _index_strategy = index_strategy.get_strategy(strategy_name)
        expected_header = f'<h2 id="{_index_strategy.strategy_name}">'
        assert expected_header.encode() in resp.content
        for _index in _index_strategy.each_subnamed_index():
            expected_row = f'<tr id="{_index.full_index_name}">'
            assert expected_row.encode() in resp.content
