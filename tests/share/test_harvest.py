from unittest import mock
import datetime
import math
import random
import threading
import uuid

import pendulum

from faker import Factory

import pytest

from django.conf import settings
from django.db import DatabaseError
from django.db import connections
from django.db import transaction

from share.harvest.exceptions import HarvesterConcurrencyError
from share.harvest.exceptions import HarvesterDisabledError
from share.models import HarvestLog
from share.models import RawDatum
from share.tasks import HarvesterTask

from tests import factories


@pytest.fixture
def source_config():
    return factories.SourceConfigFactory()


class SyncedThread(threading.Thread):

    def __init__(self, target, args=(), kwargs={}):
        self._end = threading.Event()
        self._start = threading.Event()

        def _target():
            try:
                with transaction.atomic(using='locking'):
                    target()
                    self._start.set()
                    self._end.wait(30)
            finally:
                connections.close_all()

        super().__init__(target=_target, args=args, kwargs=kwargs)

    def start(self):
        super().start()
        self._start.wait(1)

    def join(self, timeout=1):
        self._end.set()
        return super().join(timeout)


def harvest(*args, retries=99999999, task_id=None, **kwargs):
    # Set retries to be really high to avoid retrying
    return HarvesterTask().apply(args, kwargs, task_id=task_id, retries=retries)


@pytest.mark.django_db
class TestHarvestTask:

    def test_errors_on_locked(self, transactional_db, source_config):
        t = SyncedThread(source_config.acquire_lock)
        t.start()

        with pytest.raises(HarvesterConcurrencyError):
            harvest(source_config.source.user.id, source_config.label)

        t.join()

        assert HarvestLog.objects.filter(status=HarvestLog.STATUS.rescheduled).count() == 1

    def test_force_ignores_lock_error(self, source_config):
        t = SyncedThread(source_config.acquire_lock)
        t.start()

        harvest(source_config.source.user.id, source_config.label, force=True)

        t.join()

    def test_harvester_disabled(self, source_config):
        source_config.disabled = True
        source_config.save()
        with pytest.raises(HarvesterDisabledError):
            harvest(source_config.source.user.id, source_config.label)

    def test_harvester_disabled_force(self, source_config):
        source_config.disabled = True
        source_config.save()
        harvest(source_config.source.user.id, source_config.label, force=True)

    def test_harvester_disabled_ignore(self, source_config):
        source_config.disabled = True
        source_config.save()
        harvest(source_config.source.user.id, source_config.label, ignore_disabled=True)

    def test_harvest_fails(self, source_config):
        source_config.harvester.get_class().do_harvest.side_effect = ValueError('In a test')
        with pytest.raises(ValueError) as e:
            harvest(source_config.source.user.id, source_config.label)

        log = HarvestLog.objects.get(source_config=source_config)

        assert e.value.args == ('In a test', )
        assert log.status == HarvestLog.STATUS.failed
        assert log.completions == 0
        assert 'ValueError: In a test' in log.context

    def test_harvest_preapply(self, source_config):
        log = factories.HarvestLogFactory(source_config=source_config, status=HarvestLog.STATUS.failed)

        HarvesterTask._preapply(
            (1, source_config.label),
            {'start': log.start_date, 'end': log.end_date}
        )

        log.refresh_from_db()

        assert HarvestLog.objects.count() == 1
        assert log.status == HarvestLog.STATUS.retried

    def test_harvest_preapply_rescheduled(self, source_config):
        log = factories.HarvestLogFactory(source_config=source_config, status=HarvestLog.STATUS.rescheduled)

        HarvesterTask._preapply(
            (1, source_config.label),
            {'start': log.start_date, 'end': log.end_date}
        )

        log.refresh_from_db()

        assert HarvestLog.objects.count() == 1
        assert log.status == HarvestLog.STATUS.rescheduled

    def test_harvest_database_error(self, source_config):
        def do_harvest(*args, **kwargs):
            yield ('doc1', b'doc1data')
            yield ('doc2', b'doc2data')
            yield ('doc3', b'doc3data')
            raise DatabaseError('In a test')
        source_config.harvester.get_class().do_harvest.side_effect = do_harvest

        with pytest.raises(DatabaseError) as e:
            harvest(source_config.source.user.id, source_config.label)

        log = HarvestLog.objects.get(source_config=source_config)

        assert log.raw_data.count() == 0
        assert e.value.args == ('In a test', )
        assert log.status == HarvestLog.STATUS.failed
        assert log.completions == 0
        assert 'DatabaseError: In a test' in log.context

    def test_partial_harvest_fails(self, source_config):
        def do_harvest(*args, **kwargs):
            yield ('doc1', b'doc1data')
            yield ('doc2', b'doc2data')
            yield ('doc3', b'doc3data')
            raise ValueError('In a test')
        source_config.harvester.get_class().do_harvest.side_effect = do_harvest

        with pytest.raises(ValueError) as e:
            harvest(source_config.source.user.id, source_config.label)

        log = HarvestLog.objects.get(source_config=source_config)

        assert log.raw_data.count() == 3
        assert e.value.args == ('In a test', )
        assert log.status == HarvestLog.STATUS.failed
        assert log.completions == 0
        assert 'ValueError: In a test' in log.context

    def test_log_values(self, source_config):
        task_id = uuid.uuid4()
        harvest(source_config.source.user.id, source_config.label, task_id=str(task_id))
        log = HarvestLog.objects.get(source_config=source_config)

        assert log.task_id == task_id
        assert log.status == HarvestLog.STATUS.succeeded
        assert log.context == ''
        assert log.completions == 1
        assert log.start_date == (datetime.date.today() - datetime.timedelta(days=1))
        assert log.end_date == datetime.date.today()
        assert log.source_config == source_config
        assert log.share_version == settings.VERSION
        assert log.harvester_version == source_config.get_harvester().VERSION
        assert log.source_config_version == source_config.version

    def test_spawn_task(self, source_config):
        task_id = uuid.uuid4()
        harvest(source_config.source.user.id, source_config.label, task_id=str(task_id))
        log = HarvestLog.objects.get(source_config=source_config)

        assert isinstance(log.task_id, uuid.UUID)

        result = log.spawn_task(async=False)

        assert uuid.UUID(result.task_id)

    def test_spawn_task_no_task_id(self, source_config):
        task_id = uuid.uuid4()
        harvest(source_config.source.user.id, source_config.label, task_id=str(task_id))
        log = HarvestLog.objects.get(source_config=source_config)

        log.task_id = None
        log.save()

        result = log.spawn_task(async=False)

        assert uuid.UUID(result.task_id)

    def test_laziness(self, source_config):
        pass

    def test_superfluous(self, source_config):
        pass

    def test_limit(self, source_config):
        pass

    @pytest.mark.parametrize('count, rediscovered, superfluous, limit, ingest', {
        (count, int(rediscovered), False, int(limit) if limit is not None else None, True)
        for count in (0, 1, 500, 501, 1010)
        for limit in (None, 0, 1, count * .5, count, count * 2)
        for rediscovered in (0, 1, count * .5, count)
        if rediscovered <= count
    } | {
        (count, int(rediscovered), superfluous, None, ingest)
        for count in (0, 150)
        for ingest in (True, False)
        for superfluous in (True, False)
        for rediscovered in (0, count * .5, count)
        if rediscovered <= count
    })
    def test_data_flow(self, source_config, monkeypatch, count, rediscovered, superfluous, limit, ingest, django_assert_num_queries):
        assert rediscovered <= count, 'Y tho'

        fake = Factory.create()
        mock_ingest_task = mock.Mock()

        monkeypatch.setattr('share.tasks.NormalizerTask', mock_ingest_task)
        source_config.harvester.get_class().do_harvest.return_value = [(fake.sentence(), str(i * 50)) for i in range(count)]
        list(RawDatum.objects.store_chunk(source_config, random.sample(source_config.harvester.get_class().do_harvest.return_value, rediscovered)))

        # TODO Drop this number....
        with django_assert_num_queries(17 + math.ceil((count if limit is None or count < limit else limit) / 500) * 3):
            harvest(source_config.source.user.id, source_config.label, superfluous=superfluous, limit=limit, ingest=ingest)

        log = HarvestLog.objects.get(source_config=source_config)

        assert log.completions == 1
        assert log.status == HarvestLog.STATUS.succeeded
        assert log.raw_data.count() == (count if limit is None or count < limit else limit)

        if limit is not None and rediscovered:
            assert RawDatum.objects.filter().count() >= rediscovered
            assert RawDatum.objects.filter().count() <= rediscovered + max(0, min(limit, count - rediscovered))
        else:
            assert RawDatum.objects.filter().count() == (count if limit is None or count < limit else limit)

        if ingest:
            if superfluous:
                assert mock_ingest_task().apply_async.call_count == min(count, limit or 99999)
            elif limit is not None:
                assert mock_ingest_task().apply_async.call_count <= min(limit, count)
                assert mock_ingest_task().apply_async.call_count >= min(limit, count) - rediscovered
            else:
                assert mock_ingest_task().apply_async.call_count == count - rediscovered
        else:
            assert mock_ingest_task().apply_async.call_count == 0

    def test_handles_duplicate_values(self, monkeypatch, source_config):
        fake = Factory.create()
        mock_ingest_task = mock.Mock()
        monkeypatch.setattr('share.tasks.NormalizerTask', mock_ingest_task)

        source_config.harvester.get_class().do_harvest.return_value = [(fake.sentence(), str(i * 50)) for i in range(100)] * 3

        harvest(source_config.source.user.id, source_config.label, ingest=False)

        log = HarvestLog.objects.get(source_config=source_config)

        assert log.completions == 1
        assert log.status == HarvestLog.STATUS.succeeded
        assert log.raw_data.count() == 100

    def test_handles_duplicate_values_limit(self, monkeypatch, source_config):
        fake = Factory.create()
        mock_ingest_task = mock.Mock()
        monkeypatch.setattr('share.tasks.NormalizerTask', mock_ingest_task)

        padding = [(fake.sentence(), str(i * 50)) for i in range(20)]
        source_config.harvester.get_class().do_harvest.return_value = []

        for i in range(10):
            source_config.harvester.get_class().do_harvest.return_value.extend([(fake.sentence(), str(i * 50)) for i in range(5)])
            source_config.harvester.get_class().do_harvest.return_value.extend(padding)

        harvest(source_config.source.user.id, source_config.label, limit=60, ingest=False)

        log = HarvestLog.objects.get(source_config=source_config)

        assert log.completions == 1
        assert log.status == HarvestLog.STATUS.succeeded
        assert log.raw_data.count() == 60

    @pytest.mark.parametrize('start, end, result', [
        (None, None, (pendulum.parse(pendulum.today().date().isoformat()) - datetime.timedelta(days=1), pendulum.parse(pendulum.today().date().isoformat()))),
        (None, '2012-01-01', ValueError('"start" and "end" must either both be supplied or omitted')),
        ('2012-01-01', None, ValueError('"start" and "end" must either both be supplied or omitted')),
        ('2012-01-01', '2012-01-02', (pendulum.parse('2012-01-01'), pendulum.parse('2012-01-02'))),
        ('2012-01-01T00:00:00', '2012-01-02T00:00:00', (pendulum.parse('2012-01-01'), pendulum.parse('2012-01-02'))),
        ('2012-01-01T12:00:00', '2012-01-02T05:00:00', (pendulum.parse('2012-01-01'), pendulum.parse('2012-01-02'))),
        ('2012-01-01T12:00:00+04:00', '2012-01-02T05:00:00+05:00', (pendulum.parse('2012-01-01'), pendulum.parse('2012-01-02'))),
    ])
    def test_resolve_date_range(self, start, end, result):
        if isinstance(result, Exception):
            with pytest.raises(type(result)) as e:
                HarvesterTask.resolve_date_range(start, end)
            assert e.value.args == result.args
        else:
            assert HarvesterTask.resolve_date_range(start, end) == result

    def test_apply_async_defaults(self, source_config, monkeypatch):
        mock_apply_async = mock.Mock()
        monkeypatch.setattr('share.tasks.SourceTask.apply_async', mock_apply_async)

        HarvesterTask().apply_async((1, source_config.label, ))

        x = HarvestLog.objects.first()

        assert x
        assert x.end_date == datetime.date.today()
        assert x.start_date == (datetime.date.today() - datetime.timedelta(1))

    def test_apply_async_creates_log(self, source_config, monkeypatch):
        mock_apply_async = mock.Mock()
        monkeypatch.setattr('share.tasks.SourceTask.apply_async', mock_apply_async)

        HarvesterTask().apply_async((1, source_config.label, ))

        x = HarvestLog.objects.first()

        assert x
        assert x.end_date == datetime.date.today()
        assert x.start_date == (datetime.date.today() - datetime.timedelta(1))
        assert x.source_config == source_config
        assert x.status == HarvestLog.STATUS.created
        assert x.harvester_version == source_config.get_harvester().VERSION

    # def test_apply_async_resets(self, source_config, monkeypatch):
    #     mock_apply_async = mock.Mock()
    #     monkeypatch.setattr('share.tasks.SourceTask.apply_async', mock_apply_async)

    #     HarvesterTask().apply_async((source_config.label, ))

    #     x = HarvestLog.objects.first()

    # def test_log_links_does_not_shadow_original(self, source_config):
    #     HarvestLog.objects.create(
    #         source_config=config,
    #         status=HarvestLog.STATUS.succeeded,
    #         source_config_version=config.version,
    #         harvester_version=config.harvester.version,
    #     )

    # def test_failed_linking_rollsback(self, source_config):
    #     pass

    # def test_force_always_works(self, source_config):
    #     pass
