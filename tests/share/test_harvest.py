from unittest import mock
import random
import threading
import uuid

from faker import Factory

import pytest

from django.conf import settings
from django.db import DatabaseError

from share.harvest.exceptions import HarvesterConcurrencyError
from share.harvest.exceptions import HarvesterDisabledError
from share.models import Source
from share.models import HarvestLog
from share.models import RawDatum
from share import tasks

from tests import factories


@pytest.fixture
def source_config():
    return factories.SourceConfigFactory()


@pytest.fixture
def mock_transform(monkeypatch):
    mock_transform = mock.Mock()
    monkeypatch.setattr('share.tasks.transform', mock_transform)
    return mock_transform


class SyncedThread(threading.Thread):

    def __init__(self, target, args=(), kwargs={}):
        self._end = threading.Event()
        self._start = threading.Event()

        def _target(*args, **kwargs):
            with target(*args, **kwargs):
                self._start.set()
                self._end.wait(10)

        super().__init__(target=_target, args=args, kwargs=kwargs)

    def start(self):
        super().start()
        self._start.wait(10)

    def join(self, timeout=1):
        self._end.set()
        return super().join(timeout)


@pytest.mark.django_db
def test_sources_have_access_tokens():
    for source in Source.objects.all()[:10]:
        assert source.user.authorization()


@pytest.mark.django_db
class TestHarvestTaskWithLog:

    def test_not_found(self):
        with pytest.raises(HarvestLog.DoesNotExist):
            tasks.harvest(log_id=12)

    # def test_disabled_source_config(self):
    #     with pytest.raises(HarvesterConcurrencyError):
    #         tasks.harvest(log_id=12)


@pytest.mark.django_db
class TestHarvestTask:

    @pytest.mark.parametrize('source_config_kwargs, task_kwargs, lock_config, exception', [
        ({}, {}, True, HarvesterConcurrencyError),
        ({'disabled': True}, {}, True, HarvesterDisabledError),
        ({'source__is_deleted': True}, {}, True, HarvesterDisabledError),
        ({'disabled': True, 'source__is_deleted': True}, {}, True, HarvesterDisabledError),
        ({'disabled': True}, {'ignore_disabled': True}, True, HarvesterConcurrencyError),
        ({'source__is_deleted': True}, {'ignore_disabled': True}, True, HarvesterConcurrencyError),
        ({'disabled': True, 'source__is_deleted': True}, {'ignore_disabled': True}, True, HarvesterConcurrencyError),
        ({'disabled': True}, {}, False, HarvesterDisabledError),
        ({'source__is_deleted': True}, {}, False, HarvesterDisabledError),
        ({'disabled': True, 'source__is_deleted': True}, {}, False, HarvesterDisabledError),
    ])
    def test_failure_cases(self, source_config_kwargs, task_kwargs, lock_config, exception):
        source_config = factories.SourceConfigFactory(**source_config_kwargs)
        log = factories.HarvestLogFactory(source_config=source_config)

        if lock_config:
            t = SyncedThread(source_config.acquire_lock)
            t.start()

        try:
            with pytest.raises(exception):
                tasks.harvest(log_id=log.id, **task_kwargs)
        finally:
            if lock_config:
                t.join()

    @pytest.mark.parametrize('source_config_kwargs, task_kwargs, lock_config', [
        ({}, {'force': True}, True),
        ({'disabled': True}, {'force': True}, True),
        ({'disabled': True}, {'force': True}, False),
        ({'disabled': True}, {'ignore_disabled': True}, False),
        ({'source__is_deleted': True}, {'ignore_disabled': True}, False),
        ({'source__is_deleted': True}, {'force': True}, False),
        ({'source__is_deleted': True}, {'force': True}, True),
    ])
    def test_overrides(self, source_config_kwargs, task_kwargs, lock_config):
        source_config = factories.SourceConfigFactory(**source_config_kwargs)
        log = factories.HarvestLogFactory(source_config=source_config)

        if lock_config:
            t = SyncedThread(source_config.acquire_lock)
            t.start()

        try:
            tasks.harvest(log_id=log.id, **task_kwargs)
        finally:
            if lock_config:
                t.join()

    def test_harvest_fails(self, source_config):
        source_config.harvester.get_class()._do_fetch.side_effect = ValueError('In a test')
        log = factories.HarvestLogFactory(source_config=source_config)

        with pytest.raises(ValueError) as e:
            tasks.harvest(log_id=log.id)

        log.refresh_from_db()

        assert e.value.args == ('In a test', )
        assert log.status == HarvestLog.STATUS.failed
        assert log.completions == 0
        assert 'ValueError: In a test' in log.context

    def test_harvest_database_error(self, source_config, mock_transform):
        log = factories.HarvestLogFactory(source_config=source_config)

        def _do_fetch(*args, **kwargs):
            yield ('doc1', b'doc1data')
            yield ('doc2', b'doc2data')
            yield ('doc3', b'doc3data')
            raise DatabaseError('In a test')
        source_config.harvester.get_class()._do_fetch = _do_fetch

        with pytest.raises(DatabaseError) as e:
            tasks.harvest(log_id=log.id)

        log.refresh_from_db()

        assert log.raw_data.count() == 3
        assert e.value.args == ('In a test', )
        assert log.status == HarvestLog.STATUS.failed
        assert log.completions == 0
        assert 'DatabaseError: In a test' in log.context
        assert mock_transform.apply_async.call_count == 3

    def test_partial_harvest_fails(self, source_config, mock_transform):
        log = factories.HarvestLogFactory(source_config=source_config)

        def _do_fetch(*args, **kwargs):
            yield ('doc1', b'doc1data')
            yield ('doc2', b'doc2data')
            yield ('doc3', b'doc3data')
            raise ValueError('In a test')
        source_config.harvester.get_class()._do_fetch = _do_fetch

        with pytest.raises(ValueError) as e:
            tasks.harvest(log_id=log.id)

        log.refresh_from_db()

        assert log.raw_data.count() == 3
        assert e.value.args == ('In a test', )
        assert log.status == HarvestLog.STATUS.failed
        assert log.completions == 0
        assert 'ValueError: In a test' in log.context
        assert mock_transform.apply_async.call_count == 3

    def test_log_values(self, source_config):
        task_id = uuid.uuid4()
        log = factories.HarvestLogFactory(source_config=source_config)

        tasks.harvest.apply((), {'log_id': log.id}, task_id=str(task_id), throw=True)

        log.refresh_from_db()

        assert log.task_id == task_id
        assert log.status == HarvestLog.STATUS.succeeded
        assert log.context == ''
        assert log.completions == 1
        assert log.source_config == source_config
        assert log.share_version == settings.VERSION
        assert log.harvester_version == source_config.get_harvester().VERSION
        assert log.source_config_version == source_config.version

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

        monkeypatch.setattr('share.tasks.transform', mock_ingest_task)
        source_config.harvester.get_class()._do_fetch.extend([(fake.sentence(), str(i * 50)) for i in range(count)])
        list(RawDatum.objects.store_chunk(source_config, random.sample(source_config.harvester.get_class()._do_fetch, rediscovered)))

        log = factories.HarvestLogFactory(source_config=source_config)

        tasks.harvest(log_id=log.id, superfluous=superfluous, limit=limit, ingest=ingest)

        log.refresh_from_db()

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
                assert mock_ingest_task.apply_async.call_count == min(count, limit or 99999)
            elif limit is not None:
                assert mock_ingest_task.apply_async.call_count <= min(limit, count)
                assert mock_ingest_task.apply_async.call_count >= min(limit, count) - rediscovered
            else:
                assert mock_ingest_task.apply_async.call_count == count - rediscovered
        else:
            assert mock_ingest_task.apply_async.call_count == 0

    def test_handles_duplicate_values(self, monkeypatch, source_config):
        fake = Factory.create()
        log = factories.HarvestLogFactory(source_config=source_config)

        source_config.harvester.get_class()._do_fetch.extend([(fake.sentence(), str(i * 50)) for i in range(100)] * 3)

        tasks.harvest(log_id=log.id, ingest=False)

        log.refresh_from_db()

        assert log.completions == 1
        assert log.status == HarvestLog.STATUS.succeeded
        assert log.raw_data.count() == 100

    def test_handles_duplicate_values_limit(self, monkeypatch, source_config):
        fake = Factory.create()
        log = factories.HarvestLogFactory(source_config=source_config)

        padding = [(fake.sentence(), str(i * 50)) for i in range(20)]
        source_config.harvester.get_class()._do_fetch.clear()

        for i in range(10):
            source_config.harvester.get_class()._do_fetch.extend([(fake.sentence(), str(i * 50)) for i in range(5)])
            source_config.harvester.get_class()._do_fetch.extend(padding)

        tasks.harvest(log_id=log.id, limit=60, ingest=False)

        log.refresh_from_db()

        assert log.completions == 1
        assert log.status == HarvestLog.STATUS.succeeded
        assert log.raw_data.count() == 60
