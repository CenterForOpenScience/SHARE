from unittest import mock
import uuid

import pytest

from share.tasks import harvest
from share.tasks import ingest
from share.tasks.jobs import HarvestJobConsumer
from share.tasks.jobs import IngestJobConsumer
from tests import factories


@pytest.mark.parametrize('task, Consumer', [
    (harvest, HarvestJobConsumer),
    (ingest, IngestJobConsumer),
])
@pytest.mark.parametrize('kwargs', [
    {},
    {'foo': 1},
    {'foo': 1, 'bar': 'baz'},
])
def test_task_calls_consumer(task, Consumer, kwargs, monkeypatch):
    monkeypatch.setattr(Consumer, 'consume', mock.Mock())
    task.apply(kwargs=kwargs)
    assert Consumer.consume.call_count == 1
    assert Consumer.consume.call_args == ((), kwargs)


@pytest.mark.django_db
@pytest.mark.parametrize('Consumer, JobFactory', [
    (HarvestJobConsumer, factories.HarvestJobFactory),
    (IngestJobConsumer, factories.IngestJobFactory),
])
class TestJobConsumer:

    @pytest.fixture
    def consumer(self, Consumer, JobFactory, monkeypatch):
        monkeypatch.setattr(Consumer, '_consume_job', mock.Mock())
        return Consumer(task=mock.Mock(**{'request.id': uuid.uuid4()}))

    def test_no_job(self, consumer):
        consumer.consume()
        assert not consumer._consume_job.called

    def test_job_not_found(self, consumer):
        with pytest.raises(consumer.Job.DoesNotExist):
            consumer.consume(job_id=17)
        assert not consumer._consume_job.called

    def test_job_locked(self, consumer, JobFactory):
        job = JobFactory()
        with consumer.Job.objects.all().lock_first(consumer.lock_field):
            consumer.consume()
        assert not consumer._consume_job.called
        job.refresh_from_db()
        assert job.status == job.STATUS.created

    def test_skip_duplicated(self, consumer, JobFactory):
        job = JobFactory(completions=1, status=consumer.Job.STATUS.succeeded)
        consumer.consume(job_id=job.id)
        job.refresh_from_db()
        assert job.status == job.STATUS.skipped
        assert job.task_id == consumer.task.request.id
        assert not consumer._consume_job.called

    def test_obsolete(self, consumer, JobFactory, monkeypatch):
        monkeypatch.setattr(consumer.Job, 'update_versions', mock.Mock(return_value=False))
        job = JobFactory()
        consumer.consume()
        job.refresh_from_db()
        assert job.status == job.STATUS.skipped
        assert job.error_context == job.SkipReasons.obsolete.value
        assert job.task_id == consumer.task.request.id
        assert not consumer._consume_job.called

    @pytest.mark.parametrize('exhaust', [True, False])
    def test_consume(self, consumer, JobFactory, exhaust):
        job = JobFactory()
        consumer.consume(exhaust=exhaust)
        if exhaust:
            assert consumer.task.apply_async.call_count == 1
            assert consumer.task.apply_async.call_args == ((consumer.task.request.args, consumer.task.request.kwargs), {})
        else:
            assert not consumer.task.apply_async.called
        assert consumer._consume_job.call_count == 1
        assert consumer._consume_job.call_args == ((job,), {'force': False, 'superfluous': False})
