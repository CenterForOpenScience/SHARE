import contextlib
import json
import threading

from django.test import override_settings, TransactionTestCase
from django.conf import settings
from django.db import connections

from project.celery import app as celery_app
from share.search import messages
from share.search.daemon import IndexerDaemon
from share.search.index_messenger import IndexMessenger
from share.search.index_strategy import IndexStrategy
from tests import factories


ORIGINAL_ELASTICSEARCH_SETTINGS = settings.ELASTICSEARCH


def _overridden_settings(index_strategy_name):
    new_es_settings = {
        **ORIGINAL_ELASTICSEARCH_SETTINGS,
        'INDEX_STRATEGIES': {
            index_strategy_name: ORIGINAL_ELASTICSEARCH_SETTINGS['INDEX_STRATEGIES']['sharev2_elastic8'],
        }
    }
    return override_settings(ELASTICSEARCH=new_es_settings)


# using TransactionTestCase so there's NOT a transaction wrapping each test
# and the IndexerDaemon can see db changes from another thread
class TestSharev2Elastic8(TransactionTestCase):
    serialized_rollback = True

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
        self.index_strategy_name = 'test_sharev2_elastic8'
        self._overridden_settings = _overridden_settings(self.index_strategy_name)
        self._overridden_settings.enable()
        IndexStrategy.reset_strategy_cache()
        self.index_strategy = IndexStrategy.get_by_name(self.index_strategy_name)
        self.index_messenger = IndexMessenger(
            celery_app=celery_app,
            index_strategys=[self.index_strategy],
        )
        self.formatted_record = factories.FormattedMetadataRecordFactory(
            record_format='sharev2_elastic',
            formatted_metadata=json.dumps({'title': 'hello'})
        )
        self.current_index = self.index_strategy.for_current_index()
        self.current_index.pls_delete()  # in case it already exists

    def tearDown(self):
        self.current_index.pls_delete()
        self._overridden_settings.disable()
        IndexStrategy.reset_strategy_cache()

    @contextlib.contextmanager
    def _daemon_up(self):
        stop_event = threading.Event()
        IndexerDaemon.start_daemonthreads(
            celery_app,
            stop_event,
            daemonthread_context=lambda: _overridden_settings(self.index_strategy_name),
        )
        try:
            yield stop_event
        finally:
            stop_event.set()

    def test_happypath_without_daemon(self):
        self._assert_happypath_until_ingest()
        # add a record
        messages_chunk = messages.MessagesChunk(
            messages.MessageType.INDEX_SUID,
            [self.formatted_record.suid_id],
        )
        responses = list(self.index_strategy.pls_handle_messages_chunk(messages_chunk))
        assert len(responses) == 1
        assert responses[0].is_done
        assert responses[0].index_message.target_id == self.formatted_record.suid_id
        self.index_strategy.es8_client.indices.refresh(index=self.current_index.indexname)
        search_response = self.current_index.pls_handle_query__sharev2_backcompat({})
        hits = search_response['hits']['hits']
        assert len(hits) == 1
        assert hits[0]['_source'] == json.loads(self.formatted_record.formatted_metadata)
        index_status = self.current_index.pls_get_status()
        assert index_status.doc_count == 1

    def test_happypath_with_daemon(self):
        with self._daemon_up() as daemon_stop_event:
            self._assert_happypath_until_ingest()
            # add a record
            self.index_messenger.send_message(
                messages.MessageType.INDEX_SUID,
                self.formatted_record.suid_id,
            )
            for _ in range(23):
                daemon_stop_event.wait(timeout=0.2)
                self.index_strategy.es8_client.indices.refresh(index=self.current_index.indexname)
                index_status = self.current_index.pls_get_status()
                if index_status.doc_count:
                    search_response = self.current_index.pls_handle_query__sharev2_backcompat({})
                    hits = search_response['hits']['hits']
                    assert len(hits) == 1
                    assert hits[0]['_source'] == json.loads(self.formatted_record.formatted_metadata)
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
