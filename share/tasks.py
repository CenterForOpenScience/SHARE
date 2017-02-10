import abc
import datetime
import functools
import logging
import threading
import csv
import io
import gzip
import shutil
import os

import pendulum
import celery
import requests
import boto3
import botocore

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db import transaction

from share.change import ChangeGraph
from share.models import RawData, NormalizedData, ChangeSet, CeleryTask, CeleryProviderTask, ShareUser


logger = logging.getLogger(__name__)


def getter(self, attr):
    return getattr(self.context, attr)


def setter(self, value, attr):
    return setattr(self.context, attr, value)


class LoggedTask(celery.Task):
    abstract = True
    CELERY_TASK = CeleryProviderTask

    # NOTE: Celery tasks are singletons.
    # If ever running in threads/greenlets/epoll self.<var> will clobber eachother
    # this binds all the attributes that would used to a threading local object to correct that
    # Python 3.x thread locals will apparently garbage collect.
    context = threading.local()
    # Any attribute, even from subclasses, must be defined here.
    THREAD_SAFE_ATTRS = ('args', 'kwargs', 'started_by', 'source', 'task', 'normalized', 'config')
    for attr in THREAD_SAFE_ATTRS:
        locals()[attr] = property(functools.partial(getter, attr=attr)).setter(functools.partial(setter, attr=attr))

    def run(self, started_by_id, *args, **kwargs):
        # Clean up first just in case the task before crashed
        for attr in self.THREAD_SAFE_ATTRS:
            if hasattr(self.context, attr):
                delattr(self.context, attr)

        self.args = args
        self.kwargs = kwargs
        self.started_by = ShareUser.objects.get(id=started_by_id)
        self.source = None

        self.setup(*self.args, **self.kwargs)

        assert issubclass(self.CELERY_TASK, CeleryTask)
        self.task, _ = self.CELERY_TASK.objects.update_or_create(
            uuid=self.request.id,
            defaults=self.log_values(),
        )

        self.do_run(*self.args, **self.kwargs)

        # Clean up at the end to avoid keeping anything in memory
        # This is not in a finally as it may mess up sentry's exception reporting
        for attr in self.THREAD_SAFE_ATTRS:
            if hasattr(self.context, attr):
                delattr(self.context, attr)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        CeleryTask.objects.filter(uuid=task_id).update(status=CeleryTask.STATUS.retried)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        CeleryTask.objects.filter(uuid=task_id).update(status=CeleryTask.STATUS.failed)

    def on_success(self, retval, task_id, args, kwargs):
        CeleryTask.objects.filter(uuid=task_id).update(status=CeleryTask.STATUS.succeeded)

    def log_values(self):
        return {
            'name': self.name,
            'args': self.args,
            'kwargs': self.kwargs,
            'started_by': self.started_by,
            'provider': self.source,
            'status': CeleryTask.STATUS.started,
        }

    @abc.abstractmethod
    def setup(self, *args, **kwargs):
        raise NotImplementedError()

    @abc.abstractmethod
    def do_run(self):
        raise NotImplementedError()


class AppTask(LoggedTask):

    def setup(self, app_label, *args, **kwargs):
        self.config = apps.get_app_config(app_label)
        self.source = self.config.user
        self.args = args
        self.kwargs = kwargs

    def log_values(self):
        return {
            **super().log_values(),
            'app_label': self.config.label,
            'app_version': self.config.version,
        }


class HarvesterTask(AppTask):

    def apply_async(self, targs=None, tkwargs=None, **kwargs):
        tkwargs = tkwargs or {}
        tkwargs.setdefault('end', datetime.datetime.utcnow().isoformat())
        tkwargs.setdefault('start', (datetime.datetime.utcnow() + datetime.timedelta(-1)).isoformat())
        return super().apply_async(targs, tkwargs, **kwargs)

    def do_run(self, start: [str, datetime.datetime]=None, end: [str, datetime.datetime]=None, limit: int=None, force=False, **kwargs):
        if self.config.disabled and not force:
            raise Exception('Harvester {} is disabled. Either enable it or disable its celery beat entry'.format(self.config))

        if not start and not end:
            start, end = datetime.timedelta(days=-1), datetime.datetime.utcnow()
        if type(end) is str:
            end = pendulum.parse(end.rstrip('Z'))  # TODO Fix me
        if type(start) is str:
            start = pendulum.parse(start.rstrip('Z'))  # TODO Fix Me

        harvester = self.config.harvester(self.config)

        try:
            logger.info('Starting harvester run for %s %s - %s', self.config.label, start, end)
            raw_ids = harvester.harvest(start, end, limit=limit, **kwargs)
            logger.info('Collected %d data blobs from %s', len(raw_ids), self.config.label)
        except Exception as e:
            logger.exception('Failed harvester task (%s, %s, %s)', self.config.label, start, end)
            raise self.retry(countdown=10, exc=e)

        # attach task to each RawData
        RawData.tasks.through.objects.bulk_create([
            RawData.tasks.through(rawdata_id=raw_id, celeryprovidertask_id=self.task.id)
            for raw_id in raw_ids
        ])
        for raw_id in raw_ids:
            task = NormalizerTask().apply_async((self.started_by.id, self.config.label, raw_id,))
            logger.debug('Started normalizer task %s for %s', task, raw_id)


class NormalizerTask(AppTask):

    def do_run(self, raw_id):
        raw = RawData.objects.get(pk=raw_id)
        normalizer = self.config.normalizer(self.config)

        assert raw.source == self.source, 'RawData is from {}. Tried parsing it as {}'.format(raw.source, self.source)

        logger.info('Starting normalization for %s by %s', raw, normalizer)

        try:
            graph = normalizer.normalize(raw)

            if not graph['@graph']:
                logger.warning('Graph was empty for %s, skipping...', raw)
                return

            normalized_data_url = settings.SHARE_API_URL[0:-1] + reverse('api:normalizeddata-list')
            resp = requests.post(normalized_data_url, json={
                'data': {
                    'type': 'NormalizedData',
                    'attributes': {
                        'data': graph,
                        'raw': {'type': 'RawData', 'id': raw_id},
                        'tasks': [self.task.id]
                    }
                }
            }, headers={'Authorization': self.config.authorization(), 'Content-Type': 'application/vnd.api+json'})
        except Exception as e:
            logger.exception('Failed normalizer task (%s, %d)', self.config.label, raw_id)
            raise self.retry(countdown=10, exc=e)

        if (resp.status_code // 100) != 2:
            raise self.retry(countdown=10, exc=Exception('Unable to submit change graph. Received {!r}, {}'.format(resp, resp.content)))

        logger.info('Successfully submitted change for %s', raw)


class DisambiguatorTask(LoggedTask):

    def setup(self, normalized_id, *args, **kwargs):
        self.normalized = NormalizedData.objects.get(pk=normalized_id)
        self.source = self.normalized.source

    def do_run(self, *args, **kwargs):

        logger.info('%s started make JSON patches for NormalizedData %s at %s', self.started_by, self.normalized.id, datetime.datetime.utcnow().isoformat())

        try:
            with transaction.atomic():
                cg = ChangeGraph(self.normalized.data['@graph'], namespace=self.normalized.source.username)
                cg.process()
                cs = ChangeSet.objects.from_graph(cg, self.normalized.id)
                if cs and (self.source.is_robot or self.source.is_trusted):
                    # TODO: verify change set is not overwriting user created object
                    cs.accept()
        except Exception as e:
            logger.info('Failed make JSON patches for NormalizedData %s with exception %s. Retrying...', self.normalized.id, e)
            raise self.retry(countdown=10, exc=e)

        logger.info('Finished make JSON patches for NormalizedData %s by %s at %s', self.normalized.id, self.started_by, datetime.datetime.utcnow().isoformat())


class ArchiveTask(LoggedTask):

    def setup(self, *args, **kwargs):

        current_time = datetime.datetime.utcnow()
        one_day = datetime.timedelta(days=-1)
        one_week = datetime.timedelta(weeks=-1)
        two_weeks = datetime.timedelta(weeks=-2)

        # bots.elasticsearch (24hrs)
        self.elasticsearch_tasks = CeleryProviderTask.objects.filter(
            app_label='elasticsearch',
            timestamp__lt=current_time + one_day
        )
        # normalizertask (1 week)
        self.normalizer_tasks = CeleryProviderTask.objects.filter(
            name='share.tasks.NormalizerTask',
            timestamp__lt=current_time + one_week
        )
        # disambiguatortask (1 week)
        self.disambiguator_tasks = CeleryProviderTask.objects.filter(
            name='share.tasks.DisambiguatorTask',
            timestamp__lt=current_time + one_week
        )
        # harvestertask (2 weeks)
        self.harvester_tasks = CeleryProviderTask.objects.filter(
            name='share.tasks.HarvesterTask',
            timestamp__lt=current_time + two_weeks
        )
        # archivetask (2 weeks)
        self.archive_tasks = CeleryProviderTask.objects.filter(
            name='share.tasks.ArchiveTask',
            timestamp__lt=current_time + two_weeks
        )

    def do_run(self, *args, **kwargs):
        # check for storage settings
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            if os.environ.get('DEBUG', True) is False:
                raise Exception('No storage found! CeleryTasks will NOT be archived or deleted.')
            logger.warning('No storage found! CeleryTasks will NOT be archived but WILL be deleted.')

        logger.info('%s started converting queryset to csv data at %s', self.started_by, datetime.datetime.utcnow().isoformat())

        if not settings.CELERY_TASK_BUCKET_NAME:
            raise Exception('Bucket name not set! Please define bucket name in project.settings')
        bucket = self.get_bucket(settings.CELERY_TASK_BUCKET_NAME)

        if self.elasticsearch_tasks.exists():
            compressed_data = self.queryset_to_compressed_csv(self.elasticsearch_tasks)
            self.put_s3(bucket, 'elasticsearch/elasticsearch_tasks_', compressed_data)

            logger.info('Finished archiving data for Elasticsearch CeleryTask at %s', datetime.datetime.utcnow().isoformat())

            self.delete_queryset(self.elasticsearch_tasks)

        if self.normalizer_tasks.exists():
            compressed_data = self.queryset_to_compressed_csv(self.normalizer_tasks)
            self.put_s3(bucket, 'normalizer/normalizer_tasks_', compressed_data)

            logger.info('Finished archiving data for NormalizerTask at %s', datetime.datetime.utcnow().isoformat())

            self.delete_queryset(self.normalizer_tasks)

        if self.disambiguator_tasks.exists():
            compressed_data = self.queryset_to_compressed_csv(self.disambiguator_tasks)
            self.put_s3(bucket, 'disambiguator/disambiguator_tasks_', compressed_data)

            logger.info('Finished archiving data for DisambiguatorTask at %s', datetime.datetime.utcnow().isoformat())

            self.delete_queryset(self.disambiguator_tasks)

        if self.harvester_tasks.exists():
            compressed_data = self.queryset_to_compressed_csv(self.harvester_tasks)
            self.put_s3(bucket, 'harvester/harvester_tasks_', compressed_data)

            logger.info('Finished archiving data for HarvesterTask at %s', datetime.datetime.utcnow().isoformat())

            self.delete_queryset(self.harvester_tasks)

        if self.archive_tasks.exists():
            compressed_data = self.queryset_to_compressed_csv(self.archive_tasks)
            self.put_s3(bucket, 'archive/archive_tasks_', compressed_data)

            logger.info('Finished archiving data for ArchiveTask at %s', datetime.datetime.utcnow().isoformat())

            self.delete_queryset(self.archive_tasks)

    def queryset_to_compressed_csv(self, queryset):
        model = queryset.model
        compressed_output = io.BytesIO()
        output = io.StringIO()
        writer = csv.writer(output)

        headers = []
        for field in model._meta.fields:
            headers.append(field.name)
        writer.writerow(headers)

        for obj in queryset.iterator():
            row = []
            for field in headers:
                val = getattr(obj, field)
                if callable(val):
                    val = val()
                if isinstance(val, str):
                    val = val.encode("utf-8")
                row.append(val)
            writer.writerow(row)

        with gzip.GzipFile(filename='tmp.gz', mode='wb', fileobj=compressed_output) as f_out:
            f_out.write(str.encode(output.getvalue()))
        return compressed_output

    def get_bucket(self, bucket_name):
        s3 = boto3.resource('s3')
        try:
            s3.meta.client.head_bucket(Bucket=bucket_name)
        except botocore.exceptions.ClientError as e:
            # If a client error is thrown, then check that it was a 404 error.
            # If it was a 404 error, then the bucket does not exist.
            error_code = int(e.response['Error']['Code'])
            if error_code != 404:
                raise botocore.exceptions.ClientError(e)
            s3.create_bucket(Bucket=bucket_name)

        return bucket_name

    def put_s3(self, bucket, location, data):
        s3 = boto3.resource('s3')
        try:
            current_date = datetime.datetime.utcnow().isoformat()
            s3.Object(bucket, location + current_date + '.gz').put(Body=data.getvalue())
        except botocore.exceptions.ClientError as e:
            raise botocore.exceptions.ClientError(e)

    def delete_queryset(self, querySet):
        num_deleted = 0
        try:
            with transaction.atomic():
                num_deleted = querySet.delete()
        except Exception as e:
            logger.info('Failed to archive data for CeleryTask with exception %s. Retrying...', e)
            raise self.retry(countdown=10, exc=e)

        logger.info('Deleted %s CeleryTasks at %s', num_deleted, datetime.datetime.utcnow().isoformat())


class BotTask(AppTask):

    def do_run(self, last_run=None, **kwargs):
        bot = self.config.get_bot(self.started_by, last_run=last_run, **kwargs)
        logger.info('Running bot %s. Started by %s', bot, self.started_by)
        bot.run()


class ApplySingleChangeSet(celery.Task):
    def run(self, changeset_id=None, started_by_id=None):
        started_by = None
        if changeset_id is None:
            logger.error('Got null changeset_id from {}'.format(started_by_id))
            return
        if started_by_id:
            started_by = ShareUser.objects.get(pk=started_by_id)
        logger.info('{} started apply changeset for {} at {}'.format(started_by, changeset_id, datetime.datetime.utcnow().isoformat()))
        try:
            changeset = ChangeSet.objects.get(id=changeset_id, status=ChangeSet.STATUS.pending)
        except ChangeSet.DoesNotExist as ex:
            logger.exception('Changeset {} does not exist'.format(changeset_id))
        else:
            changeset.accept(save=True)


class ApplyChangeSets(celery.Task):

    def run(self, changeset_ids=list(), started_by_id=None):
        started_by = None
        if started_by_id:
            started_by = ShareUser.objects.get(pk=started_by_id)
        logger.info('{} started apply changesets for {} at {}'.format(started_by, changeset_ids, datetime.datetime.utcnow().isoformat()))

        for changeset_id in changeset_ids:
            ApplySingleChangeSet().apply_async(kwargs=dict(changeset_id=changeset_id, started_by_id=started_by_id))
