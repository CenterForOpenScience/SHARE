
import io
from unittest import mock
import pytest
from django.core.management import call_command

def run_command(*args):
    """Run a Django management command, assert that it returned as expected, and return its stdout"""
    fake_stdout = io.StringIO()
    try:
        call_command(*args, stdout=fake_stdout)
    except SystemExit:
        pass  # success!
    return fake_stdout.getvalue()

class TestCommandSearch:
    @pytest.mark.parametrize('strategy_names', [
        ['one'],
        ['another', 'makes', 'two'],
    ])
    def test_purge(self, strategy_names):
        mock_strategies = {name: mock.Mock() for name in strategy_names}

        def fake_parse_strategy_name(name):
            return mock_strategies[name]

        with mock.patch('share.search.index_strategy.parse_strategy_name', side_effect=fake_parse_strategy_name) as mock_get_strategy:
            run_command('shtrove_search_teardown', *strategy_names)

        mock_get_strategy.assert_has_calls([mock.call(name) for name in strategy_names])
        for mock_strategy in mock_strategies.values():
            mock_strategy.pls_teardown.assert_called_once_with()

    def test_setup_initial(self):
        _expected_indexes = ['baz', 'bar', 'foo']
        _mock_index_strategys = [mock.Mock(strategy_name=_name) for _name in _expected_indexes]
        with mock.patch('share.search.index_strategy.each_strategy', return_value=mock_strategies):
            run_command('shtrove_search_setup', '--initial')
        for mock_index_strategy in _mock_index_strategys:
            mock_index_strategy.pls_setup.assert_called_once_with()

    def test_setup_index(self):
        mock_index_strategy = mock.Mock()
        with mock.patch('share.search.index_strategy.get_strategy', return_value=mock_strategy):
            run_command('shtrove_search_setup', 'foo')
        mock_index_strategy.pls_setup.assert_called_once_with()

    def test_daemon(self):
        with mock.patch('share.search.daemon.IndexerDaemonControl') as mock_daemon_control:
            run_command('shtrove_indexer_run')
            mock_daemon_control.return_value.start_all_daemonthreads.assert_called_once()
