import contextlib

from django.test import override_settings, TransactionTestCase
from django.conf import settings
from django.db import connections

from project.celery import app as celery_app
from share.search.daemon import IndexerDaemon
from share.search.index_messenger import IndexMessenger
from share.search.index_strategy import IndexStrategy


ORIGINAL_ELASTICSEARCH_SETTINGS = settings.ELASTICSEARCH


# base class for testing IndexStrategy subclasses with actual elasticsearch.
# (using TransactionTestCase so there's NOT a transaction wrapping each test
# and IndexerDaemon can use a separate db connection from a separate thread)
class RealElasticTestCase(TransactionTestCase):
    serialized_rollback = True

    def get_real_strategy_name(self):
        raise NotImplementedError

    def get_test_strategy_name(self):
        raise NotImplementedError

    def get_index_strategy(self):
        return IndexStrategy.get_by_name(self.get_test_strategy_name())

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # HACK: copied from TransactionTestCase._fixture_setup; restores db
        # to the state from before TransactionTestCase clobbered it (relies
        # on how django 3.2 implements `serialized_rollback = True`, above)
        connections['default'].creation.deserialize_db_from_string(
            connections['default']._test_serialized_contents
        )

    def setUp(self):
        self.enterContext(self._settings_for_test())
        IndexStrategy.clear_strategy_cache()
        self.index_strategy = self.get_index_strategy()
        self.index_messenger = IndexMessenger(
            celery_app=celery_app,
            index_strategys=[self.index_strategy],
        )
        self.current_index = self.index_strategy.for_current_index()
        self.current_index.pls_delete()  # in case it already exists

    def tearDown(self):
        self.current_index.pls_delete()
        IndexStrategy.clear_strategy_cache()

    def enterContext(self, context_manager):
        # TestCase.enterContext added in python3.11 -- implementing here until then
        result = context_manager.__enter__()
        self.addCleanup(lambda: context_manager.__exit__(None, None, None))
        return result

    @contextlib.contextmanager
    def _daemon_up(self):
        stop_event = IndexerDaemon.start_daemonthreads(
            celery_app,
            daemonthread_context=self._settings_for_test,  # will be called in daemonthread
        )
        try:
            yield stop_event
        finally:
            stop_event.set()

    @contextlib.contextmanager
    def _settings_for_test(self):
        real_strategy_name = self.get_real_strategy_name()
        try:
            real_strategy_settings = (
                ORIGINAL_ELASTICSEARCH_SETTINGS
                ['INDEX_STRATEGIES']
                [real_strategy_name]
            )
        except KeyError:
            self.skipTest(
                f'index strategy "{real_strategy_name}" not configured in'
                " ELASTICSEARCH['INDEX_STRATEGIES'] (perhaps missing env)"
            )
        new_es_settings = {
            **ORIGINAL_ELASTICSEARCH_SETTINGS,
            'INDEX_STRATEGIES': {  # wipe out all configured strategies
                self.get_test_strategy_name(): real_strategy_settings,
            }
        }
        with override_settings(ELASTICSEARCH=new_es_settings):
            yield

    # this class implements no `test_` methods, because (per python docs):
    #   "defining test methods on base classes that are not intended to be
    # instantiated directly does not play well with [unittest.TestLoader]"
    def _assert_happypath_without_daemon(self, messages_chunk, expected_doc_count):
        self._assert_happypath_until_ingest()
        _responses = list(self.index_strategy.pls_handle_messages_chunk(messages_chunk))
        assert len(_responses) == len(messages_chunk.target_ids_chunk)
        assert all(_response.is_done for _response in _responses)
        _ids = {_response.index_message.target_id for _response in _responses}
        assert _ids == set(messages_chunk.target_ids_chunk)
        self.current_index.pls_refresh()
        _search_response = self.current_index.pls_handle_search__sharev2_backcompat()
        _hits = _search_response['hits']['hits']
        assert len(_hits) == expected_doc_count
        _index_status = self.current_index.pls_get_status()
        assert _index_status.doc_count == expected_doc_count

    def _assert_happypath_with_daemon(self, messages_chunk, expected_doc_count):
        self._assert_happypath_until_ingest()
        daemon_stop_event = self.enterContext(self._daemon_up())
        self.index_messenger.send_messages_chunk(messages_chunk)
        for _ in range(23):
            daemon_stop_event.wait(timeout=0.2)
            self.current_index.pls_refresh()
            index_status = self.current_index.pls_get_status()
            if index_status.doc_count == expected_doc_count:
                search_response = self.current_index.pls_handle_search__sharev2_backcompat()
                hits = search_response['hits']['hits']
                assert len(hits) == expected_doc_count
                break
        else:
            assert False, 'checked and waited but the daemon did not do the thing'

    def _assert_happypath_until_ingest(self):
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
