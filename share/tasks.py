import abc
import json
import logging
import datetime

import celery
import requests

from django.apps import apps
from django.conf import settings

from share.change import ChangeGraph
from share.models import RawData, NormalizedManuscript, ChangeSet, CeleryProviderTask, ShareUser


logger = logging.getLogger(__name__)


class ProviderTask(celery.Task):
    abstract = True

    def run(self, *args, **kwargs):
        app_label = args[0]
        self.config = apps.get_app_config(app_label)
        self.task, _ = CeleryProviderTask.objects.get_or_create(
            uuid=self.request.id,
            defaults={
                'name': self.name,
                'app_label': self.config.label,
                'app_version': self.config.version,
                'args': args,
                'kwargs': kwargs,
                'provider': self.config.user
            },
        )
        self.task.save()
        self.do_run(*args, **kwargs)

    @abc.abstractmethod
    def do_run(self, *args, **kwargs):
        raise NotImplementedError


class HarvesterTask(ProviderTask):

    def do_run(self, app_label, start=None, end=None, started_by=None):
        if not start and not end:
            start, end = datetime.timedelta(days=-1), datetime.datetime.utcnow()

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

            task = NormalizerTask().apply_async((self.config.label, raw.pk,), {'started_by': started_by})
            logger.debug('Started run harvester task {} for {}'.format(task, raw.id))


class NormalizerTask(ProviderTask):

    def do_run(self, app_label, raw_id, started_by=None):
        raw = RawData.objects.get(pk=raw_id)
        normalizer = self.config.normalizer(self.config)

        assert raw.source == self.config.user, 'RawData is from {}. Tried parsing it as {}'.format(self.config)

        logger.info('Starting normalization for %s by %s', raw, normalizer)

        try:
            graph = normalizer.normalize(raw)

            logger.debug('Parsed %s into %s', raw, json.dumps(graph, indent=2))

            resp = requests.post(settings.SHARE_API_URL + 'api/normalized/', json={
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
        normalized = NormalizedManuscript.objects.get(pk=normalized_id)
        normalized.tasks.add(self.task)

        logger.info('Successfully submitted change for %s', raw)


class MakeJsonPatches(celery.Task):

    def run(self, normalized_id, started_by_id=None):
        started_by = None
        normalized = NormalizedManuscript.objects.get(pk=normalized_id)
        if started_by_id:
            started_by = ShareUser.objects.get(pk=started_by_id)
        logger.info('%s started make JSON patches for %s at %s', started_by, normalized, datetime.datetime.utcnow().isoformat())

        try:
            ChangeSet.objects.from_graph(ChangeGraph.from_jsonld(normalized.normalized_data), normalized.source)
        except Exception as e:
            logger.exception('Failed make json patches (%d)', normalized_id)
            raise self.retry(countdown=10, exc=e)

        logger.info('Finished make JSON patches for %s by %s at %s', normalized, started_by, datetime.datetime.utcnow().isoformat())


class BotTask(ProviderTask):

    def do_run(self, app_label: str, started_by=None):
        config = apps.get_app_config(app_label)
        bot = config.get_bot()

        logger.info('Running bot %s. Started by %s', bot, started_by or 'system')
        bot.run()
