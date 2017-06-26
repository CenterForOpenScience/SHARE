import bz2
import datetime
import functools
import io
import logging

import boto3

from celery import states
from celery.app.task import Context
from celery.backends.base import BaseDictBackend
from celery.utils.time import maybe_timedelta

from django.conf import settings
from django.core import serializers
from django.db import transaction
from django.utils import timezone

from share.util import chunked
from share.models import CeleryTaskResult
from share.models.sql import GroupBy


logger = logging.getLogger(__name__)


if hasattr(settings, 'RAVEN_CONFIG') and settings.RAVEN_CONFIG['dsn']:
    import raven

    client = raven.Client(settings.RAVEN_CONFIG['dsn'])
else:
    client = None


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
                try:
                    if client:
                        client.captureException()
                except Exception as ee:
                    logger.exception('Could not log exception to Sentry')
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
            'meta': {
                'children': self.current_task_children(request),
            }
        }

        if status is not None:
            fields['status'] = status

        if isinstance(result, dict):
            fields['meta'].update(result)

        if isinstance(request, Context):
            fields.update({
                'task_name': request.task,
                'correlation_id': request.correlation_id,
            })

            fields['meta'].update({
                'args': request.args,
                'kwargs': request.kwargs,
            })

        obj, created = self.TaskModel.objects.get_or_create(task_id=task_id, defaults=fields)

        if not created:
            for key, value in fields.items():
                if isinstance(value, dict) and getattr(obj, key, None):
                    getattr(obj, key).update(value)
                else:
                    setattr(obj, key, value)
            obj.save()

        return obj

    @die_on_unhandled
    def cleanup(self, expires=None):
        # require storage and folder settings on prod and staging
        if settings.DEBUG is False:
            if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
                raise Exception('No storage found! CeleryTasks will NOT be archived or deleted.')
            if not settings.CELERY_TASK_FOLDER_NAME:
                raise Exception('Folder name not set! Please define folder name in project.settings')

        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            logger.warning('No storage found! CeleryTasks will NOT be archived but WILL be deleted.')
        elif not settings.CELERY_TASK_BUCKET_NAME:
            raise Exception('Bucket name not set! Please define bucket name in project.settings')

        TaskResultCleaner(expires or self.expires, bucket=settings.CELERY_TASK_BUCKET_NAME).archive()

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

    TASK_TTLS = {
        'bots.elasticsearch.tasks.index_model': datetime.timedelta(minutes=30),
        'bots.elasticsearch.tasks.index_sources': datetime.timedelta(minutes=10),
        'bots.elasticsearch.tasks.update_elasticsearch': datetime.timedelta(minutes=30),
    }

    NO_ARCHIVE = {
        'bots.elasticsearch.tasks.index_sources',
        'bots.elasticsearch.tasks.update_elasticsearch',
    }

    def __init__(self, expires, bucket=None, delete=True, chunk_size=5000):
        self.bucket = bucket
        self.chunk_size = chunk_size
        self.delete = delete
        self.expires = expires

    def get_ttl(self, task_name):
        return timezone.now() - maybe_timedelta(self.TASK_TTLS.get(task_name, self.expires))

    def get_task_names(self):
        qs = self.TaskModel.objects.values('task_name').annotate(name=GroupBy('task_name'))
        task_names = []
        for val in qs:
            if not val.get('task_name'):
                continue
            task_names.append(val.get('task_name'))
        return task_names

    def archive(self):
        for name in self.get_task_names():
            logger.debug('Looking for succeeded %s tasks modified before %s', name, self.get_ttl(name))

            queryset = self.TaskModel.objects.filter(
                task_name=name,
                status=states.SUCCESS,
                date_modified__lt=self.get_ttl(name)
            )

            if not queryset.exists():
                logger.debug('No %s tasks eligible for archival', name)
                continue

            self.archive_queryset(name, queryset)
            self.delete_queryset(queryset)

    def archive_queryset(self, task_name, queryset):
        if self.bucket is None:
            logger.warning('%r.bucket is None. Results will NOT be archived', self)
            return None

        if task_name in self.NO_ARCHIVE:
            logger.info('Found %s in NO_ARCHIVE, archival will be skipped', task_name)

        total = queryset.count()
        logger.info('Found %s %ss eligible for archiving', total, task_name)
        logger.info('Archiving in chunks of %d', self.chunk_size)

        i = 0
        for chunk in chunked(queryset.iterator(), size=self.chunk_size):
            compressed = self.compress_and_serialize(chunk)
            self.put_s3(task_name, compressed)
            i += len(chunk)
            logger.info('Archived %d of %d', i, total)

    def put_s3(self, location, data):
        obj_name = '{}/{}-{}.json.bz2'.format(
            settings.CELERY_TASK_FOLDER_NAME or '',
            location,
            timezone.now(),
        )

        boto3.resource('s3').Object(self.bucket, obj_name).put(
            Body=data.getvalue(),
            ServerSideEncryption='AES256'
        )

    def compress_and_serialize(self, queryset):
        compressed_output = io.BytesIO()
        compressed_output.write(bz2.compress(serializers.serialize('json', queryset).encode()))

        return compressed_output

    def delete_queryset(self, queryset):
        if not self.delete:
            logger.warning('%r.delete is False. Results will NOT be deleted', self)
            return 0

        total_deleted = 0

        try:
            with transaction.atomic():
                # .delete loads the entire queryset and can't be sliced... Hooray
                for ids in chunked(queryset.values_list('id', flat=True), size=self.chunk_size):
                    num_deleted, _ = queryset.model.objects.filter(id__in=ids).delete()
                    total_deleted += num_deleted
        except Exception as e:
            logger.exception('Failed to delete queryset with exception %s', e)
            raise

        logger.info('Deleted %s CeleryTasks', num_deleted)
        return total_deleted
