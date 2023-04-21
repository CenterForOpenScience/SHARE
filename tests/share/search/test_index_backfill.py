from unittest import mock

import pytest

from share.models import IndexBackfill


@pytest.mark.django_db
class TestIndexBackfillMethods:
    @pytest.fixture
    def fake_strategy(self):
        fake_strategy = mock.Mock()
        fake_strategy.name = 'foo'
        fake_strategy.for_current_index.return_value.indexname = 'foo_bar'
        return fake_strategy

    @pytest.fixture
    def index_backfill(self, fake_strategy):
        return IndexBackfill.objects.create(
            index_strategy_name=fake_strategy.name,
        )

    def test_happypath(self, index_backfill, fake_strategy):
        assert index_backfill.backfill_status == IndexBackfill.INITIAL
        assert index_backfill.specific_indexname == ''
        with mock.patch('share.tasks.schedule_index_backfill') as mock_task:
            index_backfill.pls_start(fake_strategy)
            mock_task.apply_async.assert_called_once_with((index_backfill.pk,))
        assert index_backfill.backfill_status == IndexBackfill.WAITING
        assert index_backfill.specific_indexname == 'foo_bar'
        index_backfill.pls_note_scheduling_has_begun()
        assert index_backfill.backfill_status == IndexBackfill.SCHEDULING
        index_backfill.pls_note_scheduling_has_finished()
        assert index_backfill.backfill_status == IndexBackfill.INDEXING
        index_backfill.pls_mark_complete()
        assert index_backfill.backfill_status == IndexBackfill.COMPLETE

    def test_error(self, index_backfill):
        assert index_backfill.backfill_status == IndexBackfill.INITIAL
        assert index_backfill.error_type == ''
        assert index_backfill.error_message == ''
        assert index_backfill.error_context == ''
        index_backfill.pls_mark_error(ValueError('hello'))
        assert index_backfill.backfill_status == IndexBackfill.ERROR
        assert index_backfill.error_type == 'ValueError'
        assert index_backfill.error_message == 'hello'
        assert index_backfill.error_context
        index_backfill.pls_mark_error(None)
        assert index_backfill.backfill_status == IndexBackfill.ERROR  # clearing error does not change status
        assert index_backfill.error_type == ''
        assert index_backfill.error_message == ''
        assert index_backfill.error_context == ''
