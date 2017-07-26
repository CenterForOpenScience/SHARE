import logging
import random

import celery
import requests

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.db import IntegrityError

from share.change import ChangeGraph
from share.harvest.exceptions import HarvesterConcurrencyError
from share.harvest.scheduler import HarvestScheduler
from share.models import AbstractCreativeWork
from share.models import CeleryTaskResult
from share.models import ChangeSet
from share.models import HarvestLog
from share.models import NormalizedData
from share.models import RawDatum
from share.models import Source
from share.models import SourceConfig
from share.search import SearchIndexer
from share.util.source_stat import SourceStatus
from share.util.source_stat import OAISourceStatus


logger = logging.getLogger(__name__)


@celery.shared_task(bind=True)
def transform(self, raw_id):
    raw = RawDatum.objects.select_related('suid__source_config__source__user').get(pk=raw_id)
    transformer = raw.suid.source_config.get_transformer()

    if self.request.id:
        self.update_state(meta={
            'source': raw.suid.source_config.source.long_title,
            'source_config': raw.suid.source_config.label
        })

    try:
        graph = transformer.transform(raw)

        if not graph or not graph['@graph']:
            if not raw.normalizeddata_set.exists():
                logger.warning('Graph was empty for %s, setting no_output to True', raw)
                RawDatum.objects.filter(id=raw_id).update(no_output=True)
            else:
                logger.warning('Graph was empty for %s, but a normalized data already exists for it', raw)

            return
    except Exception as e:
        logger.exception('Failed to transform %r', raw)
        raise

    resp = None
    normalized_data_url = settings.SHARE_API_URL[0:-1] + reverse('api:normalizeddata-list')

    try:
        resp = requests.post(normalized_data_url, json={
            'data': {
                'type': 'NormalizedData',
                'attributes': {
                    'data': graph,
                    'raw': {'type': 'RawData', 'id': raw_id},
                    'tasks': [CeleryTaskResult.objects.get(task_id=self.request.id).id]
                }
            }
        }, headers={'Authorization': raw.suid.source_config.source.user.authorization(), 'Content-Type': 'application/vnd.api+json'})
        resp.raise_for_status()
    except Exception as e:
        if (resp is not None) and (resp.status_code // 100 == 4):
            # If this is a 400 series response, chances are a retry isn't going to fix it.
            raise Exception('Unable to submit change graph. Received {!r}, {}'.format(resp, resp.content))
        raise self.retry(
            exc=Exception('Unable to submit change graph. Received {!r}, {}'.format(resp, resp.content if resp else e)),
            countdown=(random.random() + 1) * min(settings.CELERY_RETRY_BACKOFF_BASE ** self.request.retries, 60 * 15),
        )

    logger.info('Successfully submitted change for %s', raw)


@celery.shared_task(bind=True, max_retries=5)
def disambiguate(self, normalized_id):
    normalized = NormalizedData.objects.select_related('source__source').get(pk=normalized_id)

    if self.request.id:
        self.update_state(meta={
            'source': normalized.source.source.long_title
        })

    # Load all relevant ContentTypes in a single query
    ContentType.objects.get_for_models(*apps.get_models('share'), for_concrete_models=False)

    updated = None

    try:
        with transaction.atomic():
            cg = ChangeGraph(normalized.data['@graph'], namespace=normalized.source.username)
            cg.process()
            cs = ChangeSet.objects.from_graph(cg, normalized.id)
            if cs and (normalized.source.is_robot or normalized.source.is_trusted or Source.objects.filter(user=normalized.source).exists()):
                # TODO: verify change set is not overwriting user created object
                updated = cs.accept()
    except Exception as e:
        raise self.retry(
            exc=e,
            countdown=(random.random() + 1) * min(settings.CELERY_RETRY_BACKOFF_BASE ** self.request.retries, 60 * 15)
        )

    if not updated:
        return
    # Only index creativeworks on the fly, for the moment.
    updated_works = set(x.id for x in updated if isinstance(x, AbstractCreativeWork))
    existing_works = set(n.instance.id for n in cg.nodes if isinstance(n.instance, AbstractCreativeWork))
    ids = list(updated_works | existing_works)

    try:
        SearchIndexer(self.app).index('creativework', *ids)
    except Exception as e:
        logger.exception('Could not add results from %r to elasticqueue', normalized)
        raise


@celery.shared_task(bind=True, retries=5)
def harvest(self, log_id=None, ignore_disabled=False, ingest=True, exhaust=True, superfluous=False, force=False, limit=None):
    """Complete the harvest of the given HarvestLog or next the next available HarvestLog.

    Args:
        log_id (int, optional): Harvest the given log. Defaults to None.
            If the given log cannot be locked, the task will retry indefinitely.
            If the given log belongs to a disabled or deleted Source or SourceConfig, the task will fail.
        ingest (bool, optional): Whether or not to start the full ingest process for harvested data. Defaults to True.
        exhaust (bool, optional): Whether or not to start another harvest task if one is found. Defaults to True.
            Used to prevent a backlog of harvests. If we have a valid job, spin off another task to eat through
            the rest of the queue.
        superfluous (bool, optional): Re-ingest Rawdata that we've already collected. Defaults to False.

    """
    qs = HarvestLog.objects.all()

    if log_id is not None:
        logger.debug('Loading harvest log %d', log_id)
        qs = qs.filter(id=log_id)
    else:
        logger.debug('log_id was not specified, searching for an available log.')

        if not ignore_disabled:
            qs = qs.exclude(
                source_config__disabled=True,
            ).exclude(
                source_config__source__is_deleted=True
            )

        qs = qs.filter(
            status__in=HarvestLog.READY_STATUSES,
            end_date__lte=timezone.now().date(),
            source_config__harvest_after__lte=timezone.now().time(),
        ).unlocked('source_config')

    with qs.lock_first('source_config') as log:
        if log is None and log_id is None:
            logger.warning('No HarvestLogs are currently available')
            return None

        if log is None and log_id is not None:
            # If an id was given to us, we should have gotten a log
            log = HarvestLog.objects.get(id=log_id)  # Force the failure
            raise Exception('Failed to load {} but then found {!r}.'.format(log_id, log))  # Should never be reached

        if self.request.id:
            # Additional attributes for the celery backend
            # Allows for better analytics of currently running tasks
            self.update_state(meta={
                'log_id': log.id,
                'source': log.source_config.source.long_title,
                'source_config': log.source_config.label,
            })

            log.task_id = self.request.id
            HarvestLog.objects.filter(id=log.id).update(task_id=self.request.id)

        if log.completions > 0 and log.status == HarvestLog.STATUS.succeeded and not superfluous:
            log.skip(HarvestLog.SkipReasons.duplicated)
            logger.warning('%r has already been harvested. Force a re-run with superfluous=True', log)
            return None
        elif log.completions > 0 and log.status == HarvestLog.STATUS.succeeded:
            logger.info('%r has already been harvested. Re-running superfluously', log)

        if log.harvester_version < log.source_config.harvester.version:
            # If a harvest log has an outdated harvester_version but has not been run before, we can go ahead and upgrade it.
            # Otherwise, mark it obsolete and skip it.
            if log.completions > 0:
                log.skip(HarvestLog.SkipReasons.obsolete)
                logger.warning('%r is outdated but has previously completed, skipping...', log)
                return None

            try:
                # Attempt to upgrade the log
                with transaction.atomic():
                    log.harvester_version = log.source_config.harvester.version
                    log.save()
            except IntegrityError:
                # Sometimes a new harvest log will already be generated for one reason or another.
                # We can safely mark this log obsolete
                log.skip(HarvestLog.SkipReasons.obsolete)
                logger.warning('A newer version of %r already exists, skipping...', log)
                return None

            logger.warning('%r has been updated to the latest harvester version, %s', log, log.harvester_version)

        if exhaust and log_id is None:
            if force:
                logger.warning('propagating force=True until queue exhaustion')

            logger.debug('Spawning another harvest task')
            res = harvest.apply_async(self.request.args, self.request.kwargs)
            logger.info('Spawned %r', res)

        logger.info('Harvesting %r', log)

        try:
            for datum in log.source_config.get_harvester().harvest_from_log(log, force=force, ignore_disabled=ignore_disabled, limit=limit):
                if ingest and (datum.created or superfluous):
                    transform.apply_async((datum.id, ))
        except HarvesterConcurrencyError as e:
            # If log_id has been specified there's a chance that
            # the advisory lock was not, in fact, acquired. If so retry indefinitely to preserve
            # existing functionality
            # Use random to add jitter to help break up locking issues
            # Kinda hacky, allow a stupidly large number of retries as there is no options for infinite
            raise self.retry(
                exc=e,
                max_retries=99999,
                countdown=(random.random() + 1) * min(settings.CELERY_RETRY_BACKOFF_BASE ** self.request.retries, 60 * 15)
            )


@celery.shared_task(bind=True)
def schedule_harvests(self, *source_config_ids, cutoff=None):
    """

    Args:
        *source_config_ids (int): PKs of the source configs to schedule harvests for.
            If omitted, all non-disabled and non-deleted source configs will be scheduled
        cutoff (optional, datetime): The time to schedule harvests up to. Defaults to today.

    """
    if source_config_ids:
        qs = SourceConfig.objects.filter(id__in=source_config_ids)
    else:
        qs = SourceConfig.objects.exclude(disabled=True).exclude(source__is_deleted=True)

    with transaction.atomic():
        logs = []

        # TODO take harvest/sourceconfig version into account here
        for source_config in qs.exclude(harvester__isnull=True).select_related('harvester').annotate(latest=models.Max('harvest_logs__end_date')):
            logs.extend(HarvestScheduler(source_config).all(cutoff=cutoff, save=False))

        HarvestLog.objects.bulk_get_or_create(logs)


@celery.shared_task(bind=True)
def source_stats(self):
    oai_sourceconfigs = SourceConfig.objects.filter(
        disabled=False,
        base_url__isnull=False,
        harvester__key='oai'
    )
    for config in oai_sourceconfigs.values():
        get_source_stats.apply_async((config['id'],))

    non_oai_sourceconfigs = SourceConfig.objects.filter(
        disabled=False,
        base_url__isnull=False
    ).exclude(
        harvester__key='oai'
    )
    for config in non_oai_sourceconfigs.values():
        get_source_stats.apply_async((config['id'],))


@celery.shared_task(bind=True)
def get_source_stats(self, config_id):
    source_config = SourceConfig.objects.get(pk=config_id)
    if source_config.harvester.key == 'oai':
        OAISourceStatus(config_id).get_source_stats()
    else:
        SourceStatus(config_id).get_source_stats()
