
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
        expected_purge_calls = [
            mock.call(index_name)
            for index_name in index_names
        ]
        mock_elastic_manager = mock.Mock()
        with mock.patch('share.bin.search.ElasticManager', return_value=mock_elastic_manager):
            run_sharectl('search', 'purge', *index_names)
        assert mock_elastic_manager.delete_index.mock_calls == expected_purge_calls

    def test_setup_initial(self, settings):
        expected_indexes = ['baz', 'bar', 'foo']
        settings.ELASTICSEARCH['ACTIVE_INDEXES'] = expected_indexes
        mock_elastic_manager = mock.Mock()
        with mock.patch('share.bin.search.ElasticManager', return_value=mock_elastic_manager):
            run_sharectl('search', 'setup', '--initial')

        assert mock_elastic_manager.create_index.mock_calls == [
            mock.call(index_name)
            for index_name in expected_indexes
        ]
        assert mock_elastic_manager.update_primary_alias.mock_calls == [mock.call(expected_indexes[0])]

    def test_setup_index(self):
        mock_elastic_manager = mock.Mock()
        with mock.patch('share.bin.search.ElasticManager', return_value=mock_elastic_manager):
            run_sharectl('search', 'setup', 'foo')
        assert mock_elastic_manager.create_index.mock_calls == [mock.call('foo')]
        assert mock_elastic_manager.update_primary_alias.mock_calls == []

    def test_set_primary(self):
        mock_elastic_manager = mock.Mock()
        with mock.patch('share.bin.search.ElasticManager', return_value=mock_elastic_manager):
            run_sharectl('search', 'set_primary', 'blazblat')
        assert mock_elastic_manager.update_primary_alias.mock_calls == [mock.call('blazblat')]

    def test_daemon(self, settings):
        expected_indexes = ['bliz', 'blaz', 'bluz']
        settings.ELASTICSEARCH['ACTIVE_INDEXES'] = expected_indexes

        actual_indexes = []

        def fake_start_indexer(_, stop_event, __, index_name):
            actual_indexes.append(index_name)
            stop_event.set()

        with mock.patch('share.bin.search.SearchIndexerDaemon') as mock_daemon:
            mock_daemon.start_indexer_in_thread.side_effect = fake_start_indexer
            run_sharectl('search', 'daemon')
            assert actual_indexes == expected_indexes
