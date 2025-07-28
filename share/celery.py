import datetime
import functools
import logging

from celery import states
from celery.app.task import Context
from celery.backends.base import BaseBackend
from celery.utils.time import maybe_timedelta
from django.conf import settings
from django.db import (
    transaction,
    IntegrityError as DjIntegrityError,
    OperationalError as DjOperationalError,
)
from django.db.models import Q
from django.utils import timezone
import sentry_sdk

from share.models import CeleryTaskResult
from share.models.sql import GroupBy
from trove.util.django import pk_chunked


logger = logging.getLogger(__name__)


def die_on_unhandled(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        err = None
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err = e
            try:
                logger.exception('Celery internal method %s failed', func)
                sentry_sdk.capture_exception()
            finally:
                if err:
                    raise SystemExit(57)  # Something a bit less generic than 1 or -1
    return wrapped


# Based on https://github.com/celery/django-celery-results/commit/f88c677d66ba1eaf1b7cb1f3b8c910012990984f
class CeleryDatabaseBackend(BaseBackend):
    """

    Implemented from scratch rather than subclassed due to:
    * Meta/State information was being pushed into the results field and would ultimately get overidden by the result of the task when it finished.
    * Meta/State information was being stored as a JSON string.
      This way we can index/query that field to get information about specific types of tasks
    * IIRC, neither the task name nor the task arguments where being stored
    * The die on database connection error functionality would require reimplementing all methods.

    """
    TaskModel = CeleryTaskResult

    ###
    # decorate some methods to fully stop/restart the worker on unhandled errors,
    # including safe-to-retry errors that have been maximally retried
    # (restarting may resolve some problems; others it will merely make more visible)

    @die_on_unhandled
    def get_task_meta(self, *args, **kwargs):
        super().get_task_meta(*args, **kwargs)

    @die_on_unhandled
    def store_result(self, *args, **kwargs):
        super().store_result(*args, **kwargs)

    @die_on_unhandled
    def forget(self, *args, **kwargs):
        super().forget(*args, **kwargs)

    @die_on_unhandled
    def cleanup(self, expires=None):
        # no super implementation
        TaskResultCleaner(
            success_ttl=(expires or self.expires),
            nonsuccess_ttl=settings.FAILED_CELERY_RESULT_EXPIRES,
        ).clean()

    # END die_on_unhandled decorations
    ###

    # override BaseBackend
    def exception_safe_to_retry(self, exc):
        return isinstance(exc, (
            DjOperationalError,  # connection errors and whatnot
            DjIntegrityError,  # e.g. overlapping transactions with conflicting `get_or_create`
        ))

    # implement for BaseBackend
    def _store_result(self, task_id, result, status, traceback=None, request=None, **kwargs):
        _already_successful = (
            self.TaskModel.objects
            .filter(task_id=task_id, status=states.SUCCESS)
            .exists()
        )
        if _already_successful:
            # avoid clobbering prior successful result, which could be caused by network partition or lost worker, ostensibly:
            # https://github.com/celery/celery/blob/92514ac88afc4ccdff31f3a1018b04499607ca1e/celery/backends/base.py#L967-L972
            return

        fields = {
            'result': result,
            'traceback': traceback,
            'meta': {}
        }

        if status is not None:
            fields['status'] = status

        if isinstance(result, dict):
            fields['meta'].update(result)

        if isinstance(request, Context):
            fields.update({
                'task_name': getattr(request, 'task', None),
                'correlation_id': request.correlation_id or task_id,
            })

            fields['meta'].update({
                'args': request.args,
                'kwargs': request.kwargs,
            })

        obj, created = self.TaskModel.objects.get_or_create(task_id=task_id, defaults=fields)

        if not created:
            for key, value in fields.items():
                if getattr(obj, key, None) and isinstance(value, dict) and isinstance(getattr(obj, key), dict):
                    getattr(obj, key).update(value)
                else:
                    setattr(obj, key, value)
            obj.save()

    # implement for BaseBackend
    def _get_task_meta_for(self, task_id):
        try:
            return self.TaskModel.objects.get(task_id=task_id).as_dict()
        except self.TaskModel.DoesNotExist:
            return {'status': states.PENDING, 'result': None}

    # implement for BaseBackend
    def _forget(self, task_id):
        try:
            self.TaskModel.objects.get(task_id=task_id).delete()
        except self.TaskModel.DoesNotExist:
            pass


class TaskResultCleaner:
    """Taken from bots/archive/bot.py h/t @laurenbarker

    """

    TaskModel = CeleryTaskResult

    def __init__(self, success_ttl, nonsuccess_ttl=None, delete=True, chunk_size=5000):
        self.chunk_size = chunk_size
        self.delete = delete
        self.success_ttl = success_ttl
        self.nonsuccess_ttl = nonsuccess_ttl or success_ttl

    @property
    def success_cutoff(self) -> datetime.datetime:
        return timezone.now() - maybe_timedelta(self.success_ttl)

    @property
    def nonsuccess_cutoff(self) -> datetime.datetime:
        return timezone.now() - maybe_timedelta(self.nonsuccess_ttl)

    def get_task_names(self):
        qs = self.TaskModel.objects.values('task_name').annotate(name=GroupBy('task_name'))
        task_names = []
        for val in qs:
            if not val.get('task_name'):
                continue
            task_names.append(val.get('task_name'))
        return task_names

    def clean(self):
        for name in self.get_task_names():
            success_q = Q(status=states.SUCCESS, date_modified__lt=self.success_cutoff)
            nonsuccess_q = (
                ~Q(status=states.SUCCESS)
                & Q(date_modified__lt=self.nonsuccess_cutoff)
            )
            queryset = (
                self.TaskModel.objects
                .filter(task_name=name)
                .filter(success_q | nonsuccess_q)
            )

            if not queryset.exists():
                logger.debug('No %s tasks eligible for cleaning', name)
                continue

            self.delete_queryset(queryset)

    def delete_queryset(self, queryset):
        if not self.delete:
            logger.warning('%r.delete is False. Results will NOT be deleted', self)
            return 0

        total_deleted = 0

        try:
            with transaction.atomic():
                # .delete loads the entire queryset and can't be sliced... Hooray
                for ids in pk_chunked(queryset, chunksize=self.chunk_size):
                    num_deleted, _ = queryset.model.objects.filter(id__in=ids).delete()
                    total_deleted += num_deleted
        except Exception as e:
            logger.exception('Failed to delete queryset with exception %s', e)
            raise

        logger.info('Deleted %s CeleryTasks', total_deleted)
        return total_deleted
