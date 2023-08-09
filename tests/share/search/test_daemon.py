import contextlib
import pytest
import threading
from unittest import mock

from project.celery import app as celery_app
from share.search.daemon import (
    IndexerDaemonControl,
    MINIMUM_BACKOFF_FACTOR,
    MAXIMUM_BACKOFF_FACTOR,
    UNPRESSURED_TIMEOUT,
    MAXIMUM_BACKOFF_TIMEOUT,
    _backoff_wait,
)
from share.search import exceptions
from share.search import messages


TIMEOUT = 10  # seconds


@contextlib.contextmanager
def _daemon_running(index_strategy, *, stop_event=None, daemonthread_context=None):
    _daemon_control = IndexerDaemonControl(celery_app, stop_event=stop_event)
    try:
        _daemon = _daemon_control.start_daemonthreads_for_strategy(index_strategy)
        yield _daemon
    finally:
        _daemon_control.stop_daemonthreads()


def wait_for(event: threading.Event):
    if not event.wait(timeout=TIMEOUT):
        raise Exception('timed out waiting for event (see stack trace)')


class FakeIndexStrategyForSetupOnly:
    # for tests that don't need any message-handling
    name = 'fakefake'
    supported_message_types = {
        messages.MessageType.INDEX_SUID,
    }
    nonurgent_messagequeue_name = 'fake.nonurgent'
    urgent_messagequeue_name = 'fake.urgent'


class FakeIndexStrategyWithBlockingEvents:
    name = 'fakefake-with-events'
    supported_message_types = {
        messages.MessageType.INDEX_SUID,
    }
    nonurgent_messagequeue_name = 'fake.nonurgent'
    urgent_messagequeue_name = 'fake.urgent'

    def __init__(self):
        # these events allow pausing execution for test assertions:
        self.next_message_ready = threading.Event()
        self.next_message_released = threading.Event()
        self.message_stream_done = threading.Event()

    def pls_handle_messages_chunk(self, messages_chunk):
        self.message_stream_done.clear()
        for index_message in messages_chunk.as_tuples():
            self.next_message_ready.set()  # set so the waiting test thread will continue;
            self.next_message_ready.clear()  # clear so the test thread can wait on it again.
            self.next_message_released.clear()  # clear so this thread can...
            wait_for(self.next_message_released)  # ...wait until the test thread says go again.
            yield messages.IndexMessageResponse(True, index_message, 201, None)
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
    def test_message_ack_after_success(self):
        index_strategy = FakeIndexStrategyWithBlockingEvents()
        with _daemon_running(index_strategy) as daemon:
            message_1 = FakeCeleryMessage(messages.MessageType.INDEX_SUID, 1)
            message_2 = FakeCeleryMessage(messages.MessageType.INDEX_SUID, 2)
            daemon.on_message(message_1.payload, message_1)
            daemon.on_message(message_2.payload, message_2)
            wait_for(index_strategy.next_message_ready)
            assert not message_1.acked
            assert not message_2.acked
            index_strategy.next_message_released.set()  # daemon may continue
            wait_for(index_strategy.next_message_ready)  # wait for daemon
            assert message_1.acked
            assert not message_2.acked
            index_strategy.next_message_released.set()  # daemon may continue
            wait_for(index_strategy.message_stream_done)  # wait for daemon
            assert message_1.acked
            assert message_2.acked

    def test_unsupported_message_type(self):
        with _daemon_running(FakeIndexStrategyForSetupOnly()) as daemon:
            unsupported_message = FakeCeleryMessage(
                messages.MessageType.BACKFILL_INDEXCARD,  # anything not in supported_message_types
                1,
            )
            with pytest.raises(exceptions.DaemonMessageError):
                daemon.on_message(unsupported_message.payload, unsupported_message)
            assert not unsupported_message.acked

    def test_unexpected_error(self):
        class UnexpectedError(Exception):
            pass

        class FakeIndexStrategyWithUnexpectedError:
            name = 'fakefake_with_error'
            supported_message_types = {messages.MessageType.INDEX_SUID}
            nonurgent_messagequeue_name = 'fake.nonurgent'
            urgent_messagequeue_name = 'fake.urgent'

            def pls_handle_messages_chunk(self, messages_chunk):
                raise UnexpectedError

        with mock.patch('share.search.daemon.sentry_sdk') as mock_sentry:
            with mock.patch('share.search.daemon.logger') as mock_logger:
                with _daemon_running(
                    FakeIndexStrategyWithUnexpectedError(),
                    daemonthread_context=lambda: pytest.raises(UnexpectedError)
                ) as daemon:
                    message = FakeCeleryMessage(messages.MessageType.INDEX_SUID, 1)
                    daemon.on_message(message.payload, message)
                    assert daemon.stop_event.wait(timeout=10), (
                        'daemon should have stopped after an unexpected error'
                    )
                    mock_sentry.capture_exception.assert_called_once()
                    mock_logger.exception.assert_called_once()

    def test_noncurrent_backfill(self):
        class FakeIndexStrategyWithNoncurrentBackfill:
            name = 'fakefake-with-backfill'
            current_indexname = 'not-what-you-expected'
            supported_message_types = {messages.MessageType.BACKFILL_SUID}
            nonurgent_messagequeue_name = 'fake.nonurgent'
            urgent_messagequeue_name = 'fake.urgent'

            def get_or_create_backfill(self):
                class FakeIndexBackfill:
                    specific_indexname = 'what-you-expected'
                return FakeIndexBackfill()

        with _daemon_running(
            FakeIndexStrategyWithNoncurrentBackfill(),
            daemonthread_context=lambda: pytest.raises(exceptions.DaemonSetupError)
        ) as daemon:
            message = FakeCeleryMessage(messages.MessageType.BACKFILL_SUID, 1)
            daemon.on_message(message.payload, message)
            assert daemon.stop_event.wait(timeout=10), (
                'daemon should have stopped'
            )

    def test_message_error(self):
        class FakeIndexStrategyWithMessageError:
            name = 'fakefake_with_msg_error'
            supported_message_types = {messages.MessageType.INDEX_SUID}
            nonurgent_messagequeue_name = 'fake.nonurgent'
            urgent_messagequeue_name = 'fake.urgent'

            def pls_handle_messages_chunk(self, messages_chunk):
                for target_id in messages_chunk.target_ids_chunk:
                    yield messages.IndexMessageResponse(
                        is_done=False,
                        index_message=messages.IndexMessage(messages_chunk.message_type, target_id),
                        status_code=418,
                        error_text='i am a teapot',
                    )

        with mock.patch('share.search.daemon.sentry_sdk') as mock_sentry:
            with mock.patch('share.search.daemon.logger') as mock_logger:
                with _daemon_running(FakeIndexStrategyWithMessageError()) as daemon:
                    message = FakeCeleryMessage(messages.MessageType.INDEX_SUID, 1)
                    # error response contained
                    daemon.on_message(message.payload, message)
                    assert not daemon.stop_event.wait(timeout=1), (
                        'daemon should not have stopped for a message error'
                    )
                    # and logged
                    mock_sentry.capture_message.assert_called_once()
                    mock_logger.error.assert_called_once()
                    # but the message acked
                    assert message.acked

    @mock.patch('share.search.daemon._backoff_wait', wraps=_backoff_wait)
    def test_backoff(self, mock_backoff_wait):
        class FakeIndexStrategyWith429:
            name = 'fakefake_with_429'
            supported_message_types = {messages.MessageType.INDEX_SUID}
            nonurgent_messagequeue_name = 'fake.nonurgent'
            urgent_messagequeue_name = 'fake.urgent'
            _pls_429 = True  # set False to start responding with success

            def __init__(self):
                self.finished_chunk = threading.Event()  # to notify test thread on finish

            def pls_handle_messages_chunk(self, messages_chunk):
                for target_id in messages_chunk.target_ids_chunk:
                    if self._pls_429:
                        yield messages.IndexMessageResponse(
                            is_done=False,
                            index_message=messages.IndexMessage(messages_chunk.message_type, target_id),
                            status_code=429,
                            error_text='too many!',
                        )
                    else:
                        yield messages.IndexMessageResponse(
                            is_done=True,
                            index_message=messages.IndexMessage(messages_chunk.message_type, target_id),
                            status_code=200,
                        )
                self.finished_chunk.set()

        index_strategy = FakeIndexStrategyWith429()
        wrapped_stop_event = mock.Mock(wraps=threading.Event())
        with _daemon_running(index_strategy, stop_event=wrapped_stop_event) as daemon:
            message_list = [
                FakeCeleryMessage(messages.MessageType.INDEX_SUID, i)
                for i in range(1, 5)
            ]
            for message in message_list:
                daemon.on_message(message.payload, message)
            assert not index_strategy.finished_chunk.wait(timeout=10), (
                'should not have finished a chunk while getting 429 errors'
            )
            for message in message_list:
                assert not message.acked
            _backoff_timeouts = [
                _call.kwargs['backoff_timeout']
                for _call in mock_backoff_wait.call_args_list
            ]
            assert len(_backoff_timeouts) >= 3, 'less than 3 backoffs in 10 seconds?'
            for i in range(0, len(_backoff_timeouts)):
                _this_timeout = _backoff_timeouts[i]
                assert UNPRESSURED_TIMEOUT <= _this_timeout <= MAXIMUM_BACKOFF_TIMEOUT
                wrapped_stop_event.wait.assert_any_call(timeout=_this_timeout)
                if i > 0 and _this_timeout < MAXIMUM_BACKOFF_TIMEOUT:
                    _last_timeout = _backoff_timeouts[i - 1]
                    _backoff_factor = _this_timeout / _last_timeout
                    assert MINIMUM_BACKOFF_FACTOR <= _backoff_factor <= MAXIMUM_BACKOFF_FACTOR
            # but now the 429 errors stop
            index_strategy._pls_429 = False
            assert index_strategy.finished_chunk.wait(timeout=10), (
                'should have finished a chunk by now'
            )
            for message in message_list:
                assert message.acked
