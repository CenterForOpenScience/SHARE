import pytest
import threading

from share.search.daemon import IndexMessengerDaemon
from share.search import messages


TIMEOUT = 10  # seconds


def wait_for(event):
    if not event.wait(timeout=TIMEOUT):
        raise Exception('timed out waiting for event (see stack trace)')


class FakeIndexSetup:
    def __init__(self, index_name):
        self.index_name = index_name

        # these events allow pausing for test assertions
        self.next_message_ready = threading.Event()
        self.next_message_released = threading.Event()
        self.message_stream_done = threading.Event()

    @property
    def supported_message_types(self):
        return {messages.MessageType.INDEX_SUID}

    def pls_handle_messages(self, message_type, messages_chunk):
        self.message_stream_done.clear()
        for message in messages_chunk:
            # set so the waiting test thread will continue
            self.next_message_ready.set()
            # immediately clear so the test thread can wait on it again
            self.next_message_ready.clear()

            self.next_message_released.clear()
            wait_for(self.next_message_released)

            yield messages.HandledMessageResponse(True, message, None)
        self.message_stream_done.set()


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

    @pytest.fixture(scope='class')
    def _index_setup(self):
        return FakeIndexSetup(index_name='fake_index')

    @pytest.fixture(scope='class')
    def _daemon(self, _index_setup):
        stop_event = threading.Event()
        daemon = IndexMessengerDaemon(
            index_setup=_index_setup,
            stop_event=stop_event,
        )
        daemon.start_loops_and_queues()
        yield daemon
        stop_event.set()

    def test_message_ack_after_success(self, _index_setup, _daemon):
        message_1 = FakeCeleryMessage(messages.MessageType.INDEX_SUID, 1)
        message_2 = FakeCeleryMessage(messages.MessageType.INDEX_SUID, 2)
        _daemon.on_message(message_1.payload, message_1)
        _daemon.on_message(message_2.payload, message_2)

        wait_for(_index_setup.next_message_ready)

        assert not message_1.acked
        assert not message_2.acked
        _index_setup.next_message_released.set()

        wait_for(_index_setup.next_message_ready)

        assert message_1.acked
        assert not message_2.acked
        _index_setup.next_message_released.set()

        wait_for(_index_setup.message_stream_done)

        assert message_1.acked
        assert message_2.acked
