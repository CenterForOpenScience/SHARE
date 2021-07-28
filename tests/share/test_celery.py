import pytest
import datetime

from unittest import mock

from django.utils import timezone

from share.celery import TaskResultCleaner, CeleryTaskResult

from tests import factories


@pytest.mark.django_db
class TestResultArchiver:

    @pytest.fixture(autouse=True)
    def task_result_data(self):
        return factories.CeleryTaskResultFactory.create_batch(100)

    def test_delete_false(self):
        trc = TaskResultCleaner(datetime.timedelta(weeks=520), delete=False)
        assert trc.delete_queryset(CeleryTaskResult.objects.all()) == 0
        assert CeleryTaskResult.objects.count() != 0

    def test_delete_queryset(self):
        trc = TaskResultCleaner(datetime.timedelta(weeks=520))
        assert trc.delete_queryset(CeleryTaskResult.objects.all()) == 100
        assert CeleryTaskResult.objects.count() == 0

    def test_get_ttl_default(self):
        trc = TaskResultCleaner(datetime.timedelta(weeks=520))
        assert ((timezone.now() - datetime.timedelta(weeks=520)) - trc.get_ttl('non-existant-task')) < datetime.timedelta(seconds=2)

    def test_get_ttl(self):
        trc = TaskResultCleaner(datetime.timedelta(weeks=520))
        trc.TASK_TTLS['existant-task'] = datetime.timedelta(days=1)
        assert ((timezone.now() - datetime.timedelta(days=1)) - trc.get_ttl('existant-task')) < datetime.timedelta(seconds=2)

    def test_clean(self):
        trc = TaskResultCleaner(0, bucket=mock.Mock())
        factories.CeleryTaskResultFactory.create_batch(100, status='SUCCESS')
        trc.clean()
        assert CeleryTaskResult.objects.count() <= 100  # There's an autouse fixture that makes 100

    def test_clean_chunksize(self):
        trc = TaskResultCleaner(0, bucket=mock.Mock(), chunk_size=1)
        factories.CeleryTaskResultFactory.create_batch(100, status='SUCCESS')
        trc.clean()
        assert CeleryTaskResult.objects.count() <= 100  # There's an autouse fixture that makes 100
