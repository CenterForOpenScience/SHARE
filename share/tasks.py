import abc
import random
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
from django.db import DatabaseError
from django.db import transaction
from django.utils import timezone

from share.change import ChangeGraph
from share.models import HarvestLog
from share.models import RawDatum, NormalizedData, ChangeSet, CeleryTask, CeleryProviderTask, ShareUser, SourceConfig
from share.harvest.exceptions import HarvesterConcurrencyError, HarvesterDisabledError


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
        # TODO optimize into 1 query with ON CONFLICT
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


# Backward-compatible hack until Tamandua's all set
class SourceTask(LoggedTask):

    def setup(self, app_label, *args, **kwargs):
        self.config = SourceConfig.objects.select_related('harvester', 'transformer', 'source__user').get(label=app_label)
        self.source = self.config.source.user
        self.args = args
        self.kwargs = kwargs


class HarvesterTask(SourceTask):

    @classmethod
    def resolve_date_range(self, start, end):
        logger.debug('Coercing start and end (%r, %r) into UTC dates', start, end)

        if bool(start) ^ bool(end):
            raise ValueError('"start" and "end" must either both be supplied or omitted')

        if not start and not end:
            start, end = timezone.now() + datetime.timedelta(days=-1), timezone.now()
        if type(end) is str:
            end = pendulum.parse(end.rstrip('Z'))  # TODO Fix me
        if type(start) is str:
            start = pendulum.parse(start.rstrip('Z'))  # TODO Fix Me

        end = datetime.datetime.combine(end.date(), datetime.time(0, 0, 0, 0, timezone.utc))
        start = datetime.datetime.combine(start.date(), datetime.time(0, 0, 0, 0, timezone.utc))

        logger.debug('Interpretting start and end as %r and %r', start, end)
        return start, end

    def apply_async(self, targs=None, tkwargs=None, **kwargs):
        tkwargs = tkwargs or {}
        start, end = self.resolve_date_range(tkwargs.get('start'), tkwargs.get('end'))

        # TODO This should not be here but it's the best place too hook in right now
        config = SourceConfig.objects.select_related('harvester', 'transformer').get(label=targs[1])
        log, created = HarvestLog.objects.get_or_create(
            end_date=end,
            start_date=start,
            source_config=config,
            harvester_version=config.harvester.version,
            source_config_version=config.version,
            defaults={'status': HarvestLog.STATUS.created}
        )

        if not created and log.status != log.STATUS.rescheduled:
            log.reschedule()

        tkwargs.setdefault('end', start.isoformat())
        tkwargs.setdefault('start', start.isoformat())

        return super().apply_async(targs, tkwargs, **kwargs)

    def log_values(self):
        return {
            **super().log_values(),
            'app_label': self.config.label,
            'app_version': self.config.harvester.version,
        }

    # start and end *should* be dates. They will be turned into dates if not
    def do_run(self, start=None, end=None, limit=None, force=False, superfluous=False, ignore_disabled=False, ingest=True, **kwargs):
        # WARNING: Errors that occur here cannot be logged to the HarvestLog.
        start, end = self.resolve_date_range(start, end)
        logger.debug('Loading harvester for %r', self.config)
        harvester = self.config.get_harvester()

        # TODO optimize into 1 query with ON CONFLICT
        log, created = HarvestLog.objects.get_or_create(
            end_date=end,
            start_date=start,
            source_config=self.config,
            harvester_version=self.config.harvester.version,
            source_config_version=self.config.version,
            defaults={'task_id': self.request.id}
        )

        # TODO search for logs that contain our date range.
        if not created and log.status in (HarvestLog.STATUS.succeeded, HarvestLog.STATUS.skipped):
            if not superfluous:
                log.skip(HarvestLog.SkipReasons.duplicated)
                return logger.warning('%s - %s has already been harvested for %r. Force a re-run with superfluous=True', start, end, self.config)
            else:
                logger.info('%s - %s has already been harvested for %r. Re-running superfluously', start, end, self.config)

        # Use the locking connection to avoid putting everything else in a transaction.
        with transaction.atomic(using='locking'):
            log.start()
            error = None

            # Django recommends against trys inside of transactions, we're just preserving our lock as long as possible.
            try:
                # Attempt to lock the harvester config to make sure this is the only job making requests
                # to this specific source.
                try:
                    self.config.acquire_lock(using='locking')
                except HarvesterConcurrencyError as e:
                    if force:
                        logger.warning('Force is True; ignoring exception %r', e)
                    else:
                        raise e

                # Don't run disabled harvesters unless special cased
                if self.config.disabled and not force and not ignore_disabled:
                    raise HarvesterDisabledError('Harvester {!r} is disabled. Either enable it, run with force=True, or ignore_disabled=True'.format(self.config))

                # TODO Evaluate splitting and other optimizations here

                logger.info('Harvesting %s - %s from %r', start, end, self.config)

                with transaction.atomic():
                    datum_ids = {True: [], False: []}

                    try:
                        for datum in harvester.harvest(start, end, limit=limit, **kwargs):
                            datum_ids[datum.created].append(datum.id)
                            if datum.created:
                                logger.debug('Found new %r from %r', datum, self.config)
                            else:
                                logger.debug('Rediscovered new %r from %r', datum, self.config)
                    except DatabaseError as e:
                        # DatabaseError force the transaction to be rolled back
                        logger.exception('Database error occured while harvesting %r; bailing', self.config)
                        raise e
                    except Exception as e:
                        logger.exception('Harvesting %r failed; cleaning up', self.config)
                        error = e

                    logger.info('Collected %d new RawData from %r', len(datum_ids[True]), self.config)
                    logger.debug('Rediscovered %d RawData from %r', len(datum_ids[False]), self.config)

                    try:
                        # Attempt to populate the throughtable for any RawData that made it to the database
                        RawDatum.objects.link_to_log(log, datum_ids[True] + datum_ids[False])
                    except Exception as e:
                        logger.exception('Failed to link RawData to %r', log)
                        # Don't shadow the original error if it exists
                        if error is None and not force:
                            raise e
                        elif error is not None and force:
                            logger.warning('Force is set to True; ignoring exception')
                        else:
                            logger.warning('Harvesting also failed. Opting to raise that exception')

                if error is not None and not force:
                    logger.debug('Re-raising the harvester exception')
                    raise error
                elif error is not None and force:
                    logger.warning('Force is set to True; ignoring exception')

                if not ingest:
                    logger.warning('Not starting normalizer tasks, ingest = False')
                else:
                    for raw_id in datum_ids[True]:
                        task = NormalizerTask().apply_async((self.started_by.id, self.config.label, raw_id,))
                        logger.debug('Started normalizer task %s for %s', task, raw_id)
                    if superfluous:
                        for raw_id in datum_ids[False]:
                            task = NormalizerTask().apply_async((self.started_by.id, self.config.label, raw_id,))
                            logger.debug('Superfluously started normalizer task %s for %s', task, raw_id)

            except HarvesterConcurrencyError as e:
                # If we did not create this log and the task ids don't match. There's a very good
                # chance that this exact task is being run twice.
                # if not created and log.task_id != self.task_id and log.date_modified - datetime.datetime.utcnow() > datetime.timedelta(minutes=10):
                #     pass
                log.reschedule()
                # Kinda hacky, allow a stupidly large number of retries as there is no options for infinite
                raise self.retry(countdown=random.randrange(10, 30), exc=e, max_retries=99999)
            except Exception as e:
                log.fail(e)
                logger.exception('Failed harvester task (%r, %s, %s)', self.config, start, end)
                raise self.retry(countdown=10, exc=e)

            if force and error:
                log.forced(error)
            else:
                log.succeed()


class NormalizerTask(SourceTask):

    def do_run(self, raw_id):
        raw = RawDatum.objects.get(pk=raw_id)
        transformer = self.config.get_transformer()

        assert raw.suid.source_config_id == self.config.id, '{!r} is from {!r}. Tried parsing it as {!r}'.format(raw, raw.suid.source_config_id, self.config.id)

        logger.info('Starting normalization for %s by %s', raw, transformer)

        try:
            graph = transformer.transform(raw)

            if not graph or not graph['@graph']:
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
            }, headers={'Authorization': self.source.authorization(), 'Content-Type': 'application/vnd.api+json'})
        except Exception as e:
            logger.exception('Failed normalizer task (%s, %d)', self.config.label, raw_id)
            raise self.retry(countdown=10, exc=e)

        if (resp.status_code // 100) != 2:
            raise self.retry(countdown=10, exc=Exception('Unable to submit change graph. Received {!r}, {}'.format(resp, resp.content)))

        logger.info('Successfully submitted change for %s', raw)

    def log_values(self):
        return {
            **super().log_values(),
            'app_label': self.config.label,
            'app_version': self.config.transformer.version,
        }


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
                if cs and (self.source.is_robot or self.source.is_trusted):
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
