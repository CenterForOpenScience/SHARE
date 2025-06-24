import contextlib
from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from share.celery import TaskResultCleaner, CeleryTaskResult
from tests import factories


@contextlib.contextmanager
def long_now(new_now=None):
    _now = new_now or timezone.now()
    with mock.patch.object(timezone, 'now', return_value=_now):
        yield _now


@pytest.mark.django_db
class TestResultCleaner:

    def test_delete_false(self):
        factories.CeleryTaskResultFactory.create_batch(10)
        trc = TaskResultCleaner(timedelta(weeks=520), delete=False)
        assert trc.delete_queryset(CeleryTaskResult.objects.all()) == 0
        assert CeleryTaskResult.objects.count() == 10

    def test_delete_queryset(self):
        factories.CeleryTaskResultFactory.create_batch(10)
        trc = TaskResultCleaner(timedelta(weeks=520))
        assert trc.delete_queryset(CeleryTaskResult.objects.all()) == 10
        assert CeleryTaskResult.objects.count() == 0

    def test_success_cutoff(self, settings):
        with long_now() as _now:
            trc = TaskResultCleaner(timedelta(days=3).total_seconds())
            _expected = _now - timedelta(days=3)
            assert trc.success_cutoff == _expected

    def test_nonsuccess_cutoff(self, settings):
        with long_now() as _now:
            trc = TaskResultCleaner(
                success_ttl=timedelta(days=3),
                nonsuccess_ttl=timedelta(days=5),
            )
            assert trc.success_cutoff == _now - timedelta(days=3)
            assert trc.nonsuccess_cutoff == _now - timedelta(days=5)

    @pytest.mark.parametrize('batch_size', [1, 1111])
    def test_clean(self, batch_size):
        with long_now() as _now:
            with long_now(_now - timedelta(days=7)):
                # all should be deleted:
                factories.CeleryTaskResultFactory.create_batch(10, status='SUCCESS')
                factories.CeleryTaskResultFactory.create_batch(7, status='FAILED')
            with long_now(_now - timedelta(days=4)):
                # successes should be deleted:
                factories.CeleryTaskResultFactory.create_batch(10, status='SUCCESS')
                factories.CeleryTaskResultFactory.create_batch(7, status='FAILED')
            # none should be deleted:
            factories.CeleryTaskResultFactory.create_batch(10, status='SUCCESS')
            factories.CeleryTaskResultFactory.create_batch(7, status='FAILED')
            # end setup
            assert CeleryTaskResult.objects.count() == 51
            trc = TaskResultCleaner(
                success_ttl=timedelta(days=3),
                nonsuccess_ttl=timedelta(days=5),
                chunk_size=batch_size,
            )
            trc.clean()
            assert CeleryTaskResult.objects.filter(status='SUCCESS').count() == 10
            assert CeleryTaskResult.objects.exclude(status='SUCCESS').count() == 14
