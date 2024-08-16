
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
    @pytest.mark.parametrize('indexnames', [
        ['one'],
        ['another', 'makes', 'two'],
    ])
    def test_purge(self, indexnames):
        mock_specific_indexes = {
            indexname: mock.Mock()
            for indexname in indexnames
        }

        def _get_specific_index(indexname):
            return mock_specific_indexes[indexname]

        with mock.patch('share.bin.search.index_strategy.get_specific_index', wraps=_get_specific_index) as mock_get_specific:
            run_sharectl('search', 'purge', *indexnames)
        assert mock_get_specific.mock_calls == [
            mock.call(indexname)
            for indexname in mock_specific_indexes.keys()
        ]
        for mock_specific_index in mock_specific_indexes.values():
            mock_specific_index.pls_delete.assert_called_once_with()

    def test_setup_initial(self, settings):
        _expected_indexes = ['baz', 'bar', 'foo']
        _mock_index_strategys = {
            _name: mock.Mock()
            for _name in _expected_indexes
        }
        with patch_index_strategies(_mock_index_strategys):
            run_sharectl('search', 'setup', '--initial')
        for mock_index_strategy in _mock_index_strategys.values():
            mock_specific_index = mock_index_strategy.for_current_index.return_value
            assert mock_specific_index.pls_setup.mock_calls == [mock.call(skip_backfill=True)]

    def test_setup_index(self):
        mock_index_strategy = mock.Mock()
        with mock.patch('share.bin.search.index_strategy.get_index_strategy', return_value=mock_index_strategy):
            run_sharectl('search', 'setup', 'foo')
        mock_current_index = mock_index_strategy.for_current_index.return_value
        assert mock_current_index.pls_setup.mock_calls == [mock.call(skip_backfill=False)]

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
