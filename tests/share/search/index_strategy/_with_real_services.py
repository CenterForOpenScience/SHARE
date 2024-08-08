import contextlib
from unittest import mock

from django.test import TransactionTestCase
from django.db import connections

from project.celery import app as celery_app
from share.search.daemon import IndexerDaemonControl
from share.search.index_messenger import IndexMessenger
from share.search import index_strategy


# base class for testing IndexStrategy subclasses with actual elasticsearch.
# (using TransactionTestCase so there's NOT a transaction wrapping each test
# and IndexerDaemon can use a separate db connection from a separate thread)
class RealElasticTestCase(TransactionTestCase):
    serialized_rollback = True  # for TransactionTestCase; restore db after

    # required for subclasses
    def get_index_strategy(self) -> index_strategy.IndexStrategy:
        raise NotImplementedError(f'{self.__class__} must implement `get_index_strategy`')

    def setUp(self):
        super().setUp()
        self.enterContext(mock.patch('share.models.core._setup_user_token_and_groups'))
        self.index_strategy = self.get_index_strategy()
        self.index_messenger = IndexMessenger(
            celery_app=celery_app,
            index_strategys=[self.index_strategy],
        )
        self.current_index = self.index_strategy.for_current_index()
        self.current_index.pls_delete()  # in case it already exists
        self._assert_setup_happypath()

    def tearDown(self):
        super().tearDown()
        self.current_index.pls_delete()
        # HACK: copied from TransactionTestCase._fixture_setup; restores db
        # to the state from before TransactionTestCase clobbered it (relies
        # on how django 3.2 implements `serialized_rollback = True`, above)
        connections['default'].creation.deserialize_db_from_string(
            connections['default']._test_serialized_contents
        )

    def enterContext(self, context_manager):
        # TestCase.enterContext added in python3.11 -- implementing here until then
        result = context_manager.__enter__()
        self.addCleanup(lambda: context_manager.__exit__(None, None, None))
        return result

    @contextlib.contextmanager
    def _daemon_up(self):
        _daemon_control = IndexerDaemonControl(celery_app)
        _daemon_control.start_daemonthreads_for_strategy(self.get_index_strategy())
        try:
            yield _daemon_control
        finally:
            _daemon_control.stop_daemonthreads(wait=True)

    # for test methods on subclasses to call:
    def _assert_happypath_without_daemon(self, messages_chunk, expected_doc_count):
        _responses = list(self.index_strategy.pls_handle_messages_chunk(messages_chunk))
        assert len(_responses) == len(messages_chunk.target_ids_chunk)
        assert all(_response.is_done for _response in _responses)
        _ids = {_response.index_message.target_id for _response in _responses}
        assert _ids == set(messages_chunk.target_ids_chunk)
        self.current_index.pls_refresh()
        _search_response = self.current_index.pls_handle_search__sharev2_backcompat()
        _hits = _search_response['hits']['hits']
        assert len(_hits) == expected_doc_count

    # for test methods on subclasses to call:
    def _assert_happypath_with_daemon(self, messages_chunk, expected_doc_count):
        _daemon_control = self.enterContext(self._daemon_up())
        self.index_messenger.send_messages_chunk(messages_chunk)
        for _ in range(23):
            _daemon_control.stop_event.wait(timeout=0.2)
            self.current_index.pls_refresh()
            _search_response = self.current_index.pls_handle_search__sharev2_backcompat()
            _hits = _search_response['hits']['hits']
            if len(_hits) == expected_doc_count:
                break  # all good
        else:
            assert False, 'checked and waited but the daemon did not do the thing'

    def _assert_setup_happypath(self):
        # initial
        assert not self.current_index.pls_check_exists()
        index_status = self.current_index.pls_get_status()
        assert not index_status.creation_date
        assert not index_status.is_kept_live
        assert not index_status.is_default_for_searching
        assert not index_status.doc_count
        # create index
        self.current_index.pls_create()
        assert self.current_index.pls_check_exists()
        index_status = self.current_index.pls_get_status()
        assert index_status.creation_date
        assert not index_status.is_kept_live
        assert not index_status.is_default_for_searching
        assert not index_status.doc_count
        # keep index live (with ingested updates)
        self.current_index.pls_start_keeping_live()
        index_status = self.current_index.pls_get_status()
        assert index_status.creation_date
        assert index_status.is_kept_live
        assert not index_status.is_default_for_searching
        assert not index_status.doc_count
        # default index for searching
        self.index_strategy.pls_make_default_for_searching(self.current_index)
        index_status = self.current_index.pls_get_status()
        assert index_status.creation_date
        assert index_status.is_kept_live
        assert index_status.is_default_for_searching
        assert not index_status.doc_count
