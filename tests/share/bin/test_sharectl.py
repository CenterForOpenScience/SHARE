
import io
from contextlib import redirect_stdout

from unittest import mock
import pytest

from share.bin.util import execute_cmd
import share.version


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
    @pytest.mark.parametrize('index_names', [
        ['one'],
        ['another', 'makes', 'two'],
    ])
    def test_purge(self, index_names):
        mock_index_strategys = [
            mock.Mock()
            for _ in index_names
        ]
        with mock.patch('share.bin.search.IndexStrategy.for_all_indexes', return_value=mock_index_strategys):
            run_sharectl('search', 'purge', *index_names)
        for mock_index_strategy in mock_index_strategys:
            assert mock_index_strategy.pls_delete.mock_calls == [mock.call()]

    def test_setup_initial(self, settings):
        expected_indexes = ['baz', 'bar', 'foo']
        mock_index_strategys = [
            mock.Mock()
            for _ in expected_indexes
        ]
        with mock.patch('share.bin.search.IndexStrategy.for_all_indexes', return_value=mock_index_strategys):
            run_sharectl('search', 'setup', '--initial')
        for mock_index_strategy in mock_index_strategys:
            assert mock_index_strategy.pls_setup_as_needed.mock_calls == [mock.call()]

    def test_setup_index(self):
        mock_index_strategy = mock.Mock()
        with mock.patch('share.bin.search.IndexStrategy.by_request', return_value=mock_index_strategy):
            run_sharectl('search', 'setup', 'foo')
        assert mock_index_strategy.pls_setup_as_needed.mock_calls == [mock.call('foo')]

    def test_daemon(self, settings):
        expected_indexes = ['bliz', 'blaz', 'bluz']
        settings.ELASTICSEARCH['ACTIVE_INDEXES'] = expected_indexes

        actual_indexes = []

        def fake_start_indexer(_, stop_event, __, index_name):
            actual_indexes.append(index_name)
            stop_event.set()

        with mock.patch('share.bin.search.IndexerDaemon') as mock_daemon:
            mock_daemon.start_indexer_in_thread.side_effect = fake_start_indexer
            run_sharectl('search', 'daemon')
            assert actual_indexes == expected_indexes


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
