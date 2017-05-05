import bz2
import pytest
import datetime

from unittest import mock

from django.utils import timezone
from django.core import serializers

from share import models
from share.celery import TaskResultCleaner

from tests import factories


@pytest.mark.django_db
class TestResultArchiver:

    @pytest.fixture(autouse=True)
    def mock_boto(self, monkeypatch):
        boto = mock.Mock()
        monkeypatch.setattr('share.celery.boto3', boto)
        TaskResultCleaner.TASK_TTLS = {}
        return boto

    @pytest.fixture(autouse=True)
    def task_result_data(self):
        return factories.CeleryTaskResultFactory.create_batch(100)

    def test_delete_false(self):
        trc = TaskResultCleaner(datetime.timedelta(weeks=520), delete=False)
        assert trc.delete_queryset(models.CeleryTaskResult.objects.all()) == 0
        assert models.CeleryTaskResult.objects.count() != 0

    def test_delete_queryset(self):
        trc = TaskResultCleaner(datetime.timedelta(weeks=520))
        assert trc.delete_queryset(models.CeleryTaskResult.objects.all()) == 100
        assert models.CeleryTaskResult.objects.count() == 0

    def test_no_bucket(self):
        trc = TaskResultCleaner(datetime.timedelta(weeks=520), bucket=None)
        trc.put_s3 = mock.Mock()
        trc.archive_queryset('name', models.CeleryTaskResult.objects.all())
        assert trc.put_s3.called is False

#     @pytest.mark.parametrize('access_key, secret_key, folder_name, bucket_name', [

#     ])
#     def test_various_settings(self, settings):
#         trc = TaskResultCleaner(datetime.timedelta(years=100))

    def test_get_ttl_default(self):
        trc = TaskResultCleaner(datetime.timedelta(weeks=520))
        assert ((timezone.now() - datetime.timedelta(weeks=520)) - trc.get_ttl('non-existant-task')) < datetime.timedelta(seconds=2)

    def test_get_ttl(self):
        trc = TaskResultCleaner(datetime.timedelta(weeks=520))
        trc.TASK_TTLS['existant-task'] = datetime.timedelta(days=1)
        assert ((timezone.now() - datetime.timedelta(days=1)) - trc.get_ttl('existant-task')) < datetime.timedelta(seconds=2)

    def test_archive(self, mock_boto):
        trc = TaskResultCleaner(0, bucket=mock.Mock())
        factories.CeleryTaskResultFactory.create_batch(100, status='SUCCESS')
        trc.archive()
        assert models.CeleryTaskResult.objects.count() <= 100  # There's an autouse fixture that makes 100
        for call in mock_boto.resource('s3').Object.call_args_list:
            assert call[0][0] is trc.bucket
            assert isinstance(call[0][1], str)

    def test_archive_chunksize(self, mock_boto):
        trc = TaskResultCleaner(0, bucket=mock.Mock(), chunk_size=1)
        factories.CeleryTaskResultFactory.create_batch(100, status='SUCCESS')
        trc.archive()
        assert models.CeleryTaskResult.objects.count() <= 100  # There's an autouse fixture that makes 100
        assert len(mock_boto.resource('s3').Object.call_args_list) >= 100

    def test_serialization(self):
        trc = TaskResultCleaner(0)
        compressed = trc.compress_and_serialize(models.CeleryTaskResult.objects.all())
        reloaded = list(serializers.deserialize('json', bz2.decompress(compressed.getvalue())))
        assert len(reloaded) == 100
        for task in reloaded:
            assert isinstance(task.object, models.CeleryTaskResult)
