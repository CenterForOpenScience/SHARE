from unittest import mock

import pytest

from share.bin import main


class TestSearchCTL:

    @pytest.mark.parametrize('argv, result', [
        ('sharectl search setup', {}),
        pytest.mark.xfail(('sharectl search setup -h', {},), raises=SystemExit),
        pytest.mark.xfail(('sharectl search setup --help', {},), raises=SystemExit),
        ('sharectl search setup -i November', {'es_index': 'November'}),
        ('sharectl search setup --index Oscar', {'es_index': 'Oscar'}),
        ('sharectl search setup -u Sierra', {'es_url': 'Sierra'}),
        ('sharectl search setup --url Tango', {'es_url': 'Tango'}),
        ('sharectl search setup --url Echo --index Papa', {'es_url': 'Echo', 'es_index': 'Papa'}),
        ('sharectl search setup -u Oscar -i November', {'es_url': 'Oscar', 'es_index': 'November'}),
    ])
    def test_setup(self, argv, result):
        defaults = {'es_index': None, 'es_url': None}

        with mock.patch('share.bin.search.ElasticSearchBot') as mock_bot:
            main(argv.split(' '))

        # Assert is None to avoid accidentally ending up with a mock, ourselves
        assert mock_bot.assert_called_once_with(**{**defaults, **result}) is None

    @pytest.mark.parametrize('argv, result', [
        ('sharectl search janitor', {}),
        pytest.mark.xfail(('sharectl search janitor -h', {},), raises=SystemExit),
        pytest.mark.xfail(('sharectl search janitor --help', {},), raises=SystemExit),
        ('sharectl search janitor --d', {'dry': True}),
        ('sharectl search janitor --dry', {'dry': True}),
        ('sharectl search janitor -u Sierra', {'es_url': 'Sierra'}),
        ('sharectl search janitor -i November', {'es_index': 'November'}),
        ('sharectl search janitor --index Echo --url Kilo', {'es_url': 'Kilo', 'es_index': 'Echo'}),
    ])
    def test_janitor(self, argv, result, monkeypatch):
        defaults = {'es_index': None, 'es_url': None, 'dry': False}

        with mock.patch('share.bin.search.tasks.elasticsearch_janitor') as mock_task:
            main(argv.split(' '))

        # Assert is None to avoid accidentally ending up with a mock, ourselves
        assert mock_task.assert_called_once_with(**{**defaults, **result}) is None
