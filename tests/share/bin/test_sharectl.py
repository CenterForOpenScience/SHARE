
import io
from contextlib import redirect_stdout

from unittest import mock
import pytest

from share.bin.util import execute_cmd
import share.version

from tests.share.search import patch_index_strategies


def run_sharectl(*args):
    """run sharectl, assert that it returned as expected, and return its stdout
    """
    fake_stdout = io.StringIO()
    try:
        with redirect_stdout(fake_stdout):
            execute_cmd(args)
    except SystemExit:
        pass  # success!
    return fake_stdout.getvalue()


def test_sharectl_version():
    assert run_sharectl('-v').strip() == share.version.__version__


class TestSharectlSearch:
    @pytest.mark.parametrize('strategynames', [
        ['one'],
        ['another', 'makes', 'two'],
    ])
    def test_purge(self, strategynames):
        mock_strategies = {
            strategyname: mock.Mock()
            for strategyname in strategynames
        }

        def _fake_parse_strategy_name(strategyname):
            return mock_strategies[strategyname]

        with mock.patch('share.bin.search.index_strategy.parse_strategy_name', wraps=_fake_parse_strategy_name) as mock_get_strategy:
            run_sharectl('search', 'purge', *strategynames)
        assert mock_get_strategy.mock_calls == [
            mock.call(strategyname)
            for strategyname in mock_strategies.keys()
        ]
        for mock_strategy in mock_strategies.values():
            mock_strategy.pls_teardown.assert_called_once_with()

    def test_setup_initial(self, settings):
        _expected_indexes = ['baz', 'bar', 'foo']
        _mock_index_strategys = [
            mock.Mock(strategy_name=_name)
            for _name in _expected_indexes
        ]
        with patch_index_strategies(_mock_index_strategys):
            run_sharectl('search', 'setup', '--initial')
        for mock_index_strategy in _mock_index_strategys:
            assert mock_index_strategy.pls_setup.mock_calls == [mock.call()]

    def test_setup_index(self):
        mock_index_strategy = mock.Mock()
        with mock.patch('share.bin.search.index_strategy.get_strategy', return_value=mock_index_strategy):
            run_sharectl('search', 'setup', 'foo')
        assert mock_index_strategy.pls_setup.mock_calls == [mock.call()]

    def test_daemon(self, settings):
        with mock.patch('share.bin.search.IndexerDaemonControl') as mock_daemon_control:
            run_sharectl('search', 'daemon')
            mock_daemon_control.return_value.start_all_daemonthreads.assert_called_once()


# TODO unit tests, not just a smoke test
def test_fetch_runs():
    with mock.patch('share.bin.harvest.SourceConfig'):
        run_sharectl('fetch', 'foo.sourceconfig', '2021-05-05', '--print')


# TODO unit tests, not just a smoke test
def test_harvest_runs():
    with mock.patch('share.bin.harvest.SourceConfig'):
        run_sharectl('harvest', 'foo.sourceconfig')


# TODO unit tests, not just a smoke test
def test_schedule_runs():
    with mock.patch('share.bin.harvest.SourceConfig'):
        with mock.patch('share.bin.harvest.HarvestScheduler'):
            with mock.patch('share.bin.harvest.tasks'):
                run_sharectl('schedule', 'foo.sourceconfig')
