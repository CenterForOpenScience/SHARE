import datetime
import functools
import logging

from celery import states
from celery.app.task import Context
from celery.backends.base import BaseDictBackend
from celery.utils.time import maybe_timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

import sentry_sdk

from share.util import chunked
from share.models import CeleryTaskResult
from share.models.sql import GroupBy


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
class CeleryDatabaseBackend(BaseDictBackend):
    """

    Implemented from scratch rather than subclassed due to:
    * Meta/State information was being pushed into the results field and would ultimately get overidden by the result of the task when it finished.
    * Meta/State information was being stored as a JSON string.
      This way we can index/query that field to get information about specific types of tasks
    * IIRC, neither the task name nor the task arguments where being stored
    * The die on database connection error functionality would require reimplementing all methods.

    """
    TaskModel = CeleryTaskResult

    @die_on_unhandled
    def _store_result(self, task_id, result, status, traceback=None, request=None, **kwargs):
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

        return obj

    @die_on_unhandled
    def cleanup(self, expires=None):
        TaskResultCleaner(
            success_ttl=(expires or self.expires),
            nonsuccess_ttl=settings.FAILED_CELERY_RESULT_EXPIRES,
        ).clean()

    @die_on_unhandled
    def _get_task_meta_for(self, task_id):
        return self.TaskModel.objects.get(task_id=task_id).as_dict()

    @die_on_unhandled
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
                for ids in chunked(queryset.values_list('id', flat=True).iterator(), size=self.chunk_size):
                    num_deleted, _ = queryset.model.objects.filter(id__in=ids).delete()
                    total_deleted += num_deleted
        except Exception as e:
            logger.exception('Failed to delete queryset with exception %s', e)
            raise

        logger.info('Deleted %s CeleryTasks', total_deleted)
        return total_deleted
