import abc
import logging
import datetime

import arrow
import celery
import requests

from django.apps import apps
from django.conf import settings
from django.core.urlresolvers import reverse

from share.change import ChangeGraph
from share.models import RawData, NormalizedData, ChangeSet, CeleryProviderTask, ShareUser


logger = logging.getLogger(__name__)


class ProviderTask(celery.Task):
    abstract = True

    def run(self, app_label, started_by, *args, **kwargs):
        self.config = apps.get_app_config(app_label)
        self.started_by = ShareUser.objects.get(id=started_by)

        self.task, _ = CeleryProviderTask.objects.update_or_create(
            uuid=self.request.id,
            defaults={
                'name': self.name,
                'app_label': self.config.label,
                'app_version': self.config.version,
                'args': args,
                'kwargs': kwargs,
                'status': CeleryProviderTask.STATUS.started,
                'provider': self.config.user,
                'started_by': self.started_by,
            },
        )
        self.do_run(*args, **kwargs)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        CeleryProviderTask.objects.filter(uuid=task_id).update(status=CeleryProviderTask.STATUS.retried)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        CeleryProviderTask.objects.filter(uuid=task_id).update(status=CeleryProviderTask.STATUS.failed)

    def on_success(self, retval, task_id, args, kwargs):
        CeleryProviderTask.objects.filter(uuid=task_id).update(status=CeleryProviderTask.STATUS.succeeded)

    @abc.abstractmethod
    def do_run(self, *args, **kwargs):
        raise NotImplementedError


class HarvesterTask(ProviderTask):

    def do_run(self, start: [str, datetime.datetime]=None, end: [str, datetime.datetime]=None):
        if self.config.disabled:
            raise Exception('Harvester {} is disabled. Either enable it or disable it\'s celery beat entry'.format(self.config))

        if not start and not end:
            start, end = datetime.timedelta(days=-1), datetime.datetime.utcnow()
        if type(end) is str:
            end = arrow.get(end).datetime
        if type(start) is str:
            start = arrow.get(start).datetime

        harvester = self.config.harvester(self.config)

        try:
            logger.info('Starting harvester run for %s %s - %s', self.config.label, start, end)
            raws = harvester.harvest(start, end)
            logger.info('Collected %d data blobs from %s', len(raws), self.config.label)
        except Exception as e:
            logger.exception('Failed harvester task (%s, %s, %s)', self.config.label, start, end)
            raise self.retry(countdown=10, exc=e)

        for raw in raws:
            # attach task
            raw.tasks.add(self.task)

            task = NormalizerTask().apply_async((self.config.label, self.started_by.id, raw.pk,))
            logger.debug('Started normalizer task %s for %s', task, raw.id)


class NormalizerTask(ProviderTask):

    def do_run(self, raw_id):
        raw = RawData.objects.get(pk=raw_id)
        normalizer = self.config.normalizer(self.config)

        assert raw.source == self.config.user, 'RawData is from {}. Tried parsing it as {}'.format(raw.source, self.config)

        logger.info('Starting normalization for %s by %s', raw, normalizer)

        try:
            graph = normalizer.normalize(raw)

            if not graph['@graph']:
                logger.warning('Graph was empty for %s, skipping...', raw)
                return

            normalized_data_url = settings.SHARE_API_URL[0:-1] + reverse('api:normalizeddata-list')
            resp = requests.post(normalized_data_url, json={
                'created_at': datetime.datetime.utcnow().isoformat(),
                'normalized_data': graph,
            }, headers={'Authorization': self.config.authorization()})
        except Exception as e:
            logger.exception('Failed normalizer task (%s, %d)', self.config.label, raw_id)
            raise self.retry(countdown=10, exc=e)

        if (resp.status_code // 100) != 2:
            raise self.retry(countdown=10, exc=Exception('Unable to submit change graph. Received {!r}, {}'.format(resp, resp.content)))

        # attach task
        normalized_id = resp.json()['normalized_id']
        normalized = NormalizedData.objects.get(pk=normalized_id)
        normalized.raw = raw
        normalized.tasks.add(self.task)
        normalized.save()

        logger.info('Successfully submitted change for %s', raw)


class MakeJsonPatches(celery.Task):

    def run(self, normalized_id, started_by_id=None):
        started_by = None
        normalized = NormalizedData.objects.get(pk=normalized_id)
        if started_by_id:
            started_by = ShareUser.objects.get(pk=started_by_id)
        logger.info('%s started make JSON patches for %s at %s', started_by, normalized, datetime.datetime.utcnow().isoformat())

        try:
            cs = ChangeSet.objects.from_graph(ChangeGraph.from_jsonld(normalized.normalized_data, extra_namespace=normalized.source.username), normalized.id)
            if cs and normalized.source.is_robot:
                # TODO: verify change set is not overwriting user created object
                cs.accept()
        except Exception as e:
            logger.exception('Failed make json patches (%d)', normalized_id)
            raise self.retry(countdown=10, exc=e)

        logger.info('Finished make JSON patches for %s by %s at %s', normalized, started_by, datetime.datetime.utcnow().isoformat())


class BotTask(ProviderTask):

    def do_run(self, last_run=None):
        bot = self.config.get_bot(self.started_by, last_run=last_run)
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
