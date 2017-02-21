import threading
import pytest
import datetime
from share.models import HarvestLog
from share.models import SourceConfig
from share.harvest import BaseHarvester
from share.tasks import HarvesterTask
from unittest import mock

from django.db import transaction

from share.harvest.exceptions import HarvesterConcurrencyError, HarvesterDisabledError

from tests.share import factories


@pytest.fixture
def source_config():
    source_config = factories.SourceConfigFactory()

    class MockHarvester(BaseHarvester):
        KEY = source_config.harvester.key
        VERSION = '0.0.0'

        do_harvest = mock.Mock()
        _rawdata = []

    def do_harvest(*args, **kwargs):
        for i in MockHarvester._rawdata:
            yield i
    source_config.harvester.get_class().do_harvest.side_effect = do_harvest

    return source_config


@pytest.fixture
def committed_source_config(transactional_db):
    source_config = factories.SourceConfigFactory()

    class MockHarvester(BaseHarvester):
        KEY = source_config.harvester.key
        VERSION = '0.0.0'

        do_harvest = mock.Mock()
        _rawdata = []

    def do_harvest(*args, **kwargs):
        for i in MockHarvester._rawdata:
            yield i
    source_config.harvester.get_class().do_harvest.side_effect = do_harvest

    return source_config


class SyncedThread(threading.Thread):

    def __init__(self, target, args=(), kwargs={}):
        self._end = threading.Event()
        self._start = threading.Event()

        def _target():
            with transaction.atomic(using='locking'):
                target()
                self._start.set()
                self._end.wait(1)

        super().__init__(target=_target, args=args, kwargs=kwargs)

    def start(self):
        super().start()
        self._start.wait()

    def join(self, timeout=1):
        self._end.set()
        return super().join(timeout)


def harvest(*args, **kwargs):
    # Set retries to be really high to avoid retrying
    return HarvesterTask().apply(args, kwargs, retries=999)


@pytest.mark.django_db
class TestHarvestTask:

    def test_succeeds(self, source_config):
        harvest(source_config.source.user.id, source_config.label)
        assert HarvestLog.objects.filter(status=HarvestLog.STATUS.succeeded).count() == 1

    def test_errors_on_locked(self, committed_source_config):
        t = SyncedThread(committed_source_config.acquire_lock)
        t.start()

        with pytest.raises(HarvesterConcurrencyError):
            harvest(committed_source_config.source.user.id, committed_source_config.label)

        t.join()

        assert HarvestLog.objects.filter(status=HarvestLog.STATUS.rescheduled).count() == 1

    def test_force_ignores_lock_error(self, committed_source_config):
        t = SyncedThread(committed_source_config.acquire_lock)
        t.start()

        harvest(committed_source_config.source.user.id, committed_source_config.label, force=True)

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

    def test_marks_log_failed_with_tb(self, source_config):
        pass

    def test_links_partial_results(self, source_config):
        pass

    def test_log_links_does_not_shadow_original(self, source_config):
        pass

    def test_failed_linking_rollsback(self, source_config):
        pass

    def test_starts_ingest_tasks(self, source_config):
        pass

    def test_does_not_start_ingest_tasks(self, source_config):
        pass

    def test_force_start_ingest_tasks(self, source_config):
        pass

    def test_increments_completions(self, source_config):
        pass
