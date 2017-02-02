import abc
import datetime
import functools
import logging
import threading

import pendulum
import celery
import requests

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
        # Load all relevant ContentTypes in a single query
        ContentType.objects.get_for_models(*apps.get_models('share'), for_concrete_models=False)

        logger.info('%s started make JSON patches for NormalizedData %s at %s', self.started_by, self.normalized.id, datetime.datetime.utcnow().isoformat())

        try:
            with transaction.atomic():
                cg = ChangeGraph(self.normalized.data['@graph'], namespace=self.normalized.source.username)
                cg.process()
                cs = ChangeSet.objects.from_graph(cg, self.normalized.id)
                if cs and (self.source.is_robot or self.source.is_trusted or self.source.username == settings.APPLICATION_USERNAME):
                    # TODO: verify change set is not overwriting user created object
                    cs.accept()
        except Exception as e:
            logger.info('Failed make JSON patches for NormalizedData %s with exception %s. Retrying...', self.normalized.id, e)
            raise self.retry(countdown=10, exc=e)

        logger.info('Finished make JSON patches for NormalizedData %s by %s at %s', self.normalized.id, self.started_by, datetime.datetime.utcnow().isoformat())


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
