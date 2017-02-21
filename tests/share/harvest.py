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


# class TestHarvestLog:

#     def test_m2m(self):
#         pass


# class TestHarvestResolveArgs:

#     @pytest.mark.parametrize('input, expected', [
#         (0, datetime.fromtimestamp(0)),
#         (500000, datetime.fromtimestamp(500000)),
#         ('2010-02-10', datetime.fromtimestamp(0)),
#     ])
#     def test_resolve(self):
#         d.tzinfo is None or d.tzinfo.utcoffset(d) is None


# class TestHarvestTaskLog:

#     def test_disabled_harvester(self):
#         pass

#     def test_failed_harvest(self):
#         pass

#     def test_succeeds(self):
#         pass


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


@pytest.mark.django_db
class TestHarvestTask:

    def test_succeeds(self, source_config, django_assert_num_queries):
        # Set retries to be really high to avoid retrying
        with django_assert_num_queries(2):
            HarvesterTask().apply((source_config.source.user.id, source_config.label, ), retries=999)
        assert HarvestLog.objects.filter(status=HarvestLog.STATUS.succeeded).count() == 1

    def test_errors_on_locked(self, committed_source_config):
        t = SyncedThread(committed_source_config.acquire_lock)
        t.start()

        with pytest.raises(HarvesterConcurrencyError):
            HarvesterTask().apply((committed_source_config.source.user.id, committed_source_config.label, ), retries=999)

        t.join()

        assert HarvestLog.objects.filter(status=HarvestLog.STATUS.reschedule).count() == 1

    def test_force_ignores_lock_error(self, committed_source_config):
        t = SyncedThread(committed_source_config.acquire_lock)
        t.start()

        HarvesterTask().apply((committed_source_config.source.user.id, committed_source_config.label, ), {'force': True}, retries=999)

        t.join()

    def test_harvester_disabled(self, source_config):
        source_config.disabled = True
        source_config.save()
        with pytest.raises(HarvesterDisabledError):
            HarvesterTask().apply((source_config.source.user.id, source_config.label, ), retries=999)

    def test_harvester_disabled_force(self, source_config):
        source_config.disabled = True
        source_config.save()
        HarvesterTask().apply((source_config.source.user.id, source_config.label, ), {'force': True}, retries=999)

    def test_harvester_disabled_ignore(self, source_config):
        source_config.disabled = True
        source_config.save()
        HarvesterTask().apply((source_config.source.user.id, source_config.label, ), {'ignore_disabled': True}, retries=999)

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
