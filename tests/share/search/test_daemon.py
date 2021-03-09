import pytest
import threading

from share.search.daemon import SearchIndexerDaemon
from share.search.messages import MessageType


TIMEOUT = 10  # seconds


def wait_for(event):
    if not event.wait(timeout=TIMEOUT):
        raise Exception('timed out waiting for event (see stack trace)')


class FakeElasticManager:
    def __init__(self, expected_index_name, block_each_action=True):
        self.expected_index_name = expected_index_name
        self.block_each_action = block_each_action

        self.next_action_ready = threading.Event()
        self.next_action_released = threading.Event()
        self.action_stream_done = threading.Event()

        # only what's necessary
        self.settings = {
            'CHUNK_SIZE': 17,
        }

    def get_index_setup(self, index_name):
        assert index_name == self.expected_index_name
        return FakeIndexSetup()

    def stream_actions(self, actions):
        self.action_stream_done.clear()
        for action in actions:
            if self.block_each_action:
                # set so the waiting test thread will continue
                self.next_action_ready.set()
                # immediately clear so the test thread can wait on it again
                self.next_action_ready.clear()

                self.next_action_released.clear()
                wait_for(self.next_action_released)

            yield (True, 'fake_op_type', action)
        self.action_stream_done.set()

    # ElasticManager methods that aren't (shouldn't be) used in these tests:
    #
    # def delete_index(self, index_name):
    #
    # def create_index(self, index_name):


class FakeIndexSetup:
    @property
    def supported_message_types(self):
        return {MessageType.INDEX_SUID}

    def build_action_generator(self, index_name, message_type):
        def _fake_action_generator(target_id_iter):
            for target_id in target_id_iter:
                yield (target_id, {'_id': target_id, '_type': message_type.value})
        return _fake_action_generator

    # IndexSetup methods that aren't (shouldn't be) used in these tests
    #
    # @property
    # def index_settings(self):
    #
    # @property
    # def index_mappings(self):
    #
    # def build_and_cache_source_doc(self, message_type, target_id):


class FakeCeleryMessage:

    def __init__(self, message_type, target_id):
        self.payload = {
            'version': 2,
            'message_type': message_type.value,
            'target_id': target_id,
        }
        self.acked = False

    def ack(self):
        self.acked = True
        return True


class TestIndexerDaemon:

    @pytest.fixture
    def _action_sent_event(self):
        return threading.Event()

    @pytest.fixture(scope='class')
    def _manager(self):
        return FakeElasticManager(expected_index_name='fake_index')

    @pytest.fixture(scope='class')
    def _daemon(self, _manager):
        stop_event = threading.Event()
        daemon = SearchIndexerDaemon(
            index_name='fake_index',
            elastic_manager=_manager,
            stop_event=stop_event,
        )
        daemon.start_loops_and_queues()
        yield daemon
        stop_event.set()

    def test_message_ack_after_action_success(self, _manager, _daemon):
        message_1 = FakeCeleryMessage(MessageType.INDEX_SUID, 1)
        message_2 = FakeCeleryMessage(MessageType.INDEX_SUID, 2)
        _daemon.on_message(message_1.payload, message_1)
        _daemon.on_message(message_2.payload, message_2)

        wait_for(_manager.next_action_ready)

        assert not message_1.acked
        assert not message_2.acked
        _manager.next_action_released.set()

        wait_for(_manager.next_action_ready)

        assert message_1.acked
        assert not message_2.acked
        _manager.next_action_released.set()

        wait_for(_manager.action_stream_done)

        assert message_1.acked
        assert message_2.acked
