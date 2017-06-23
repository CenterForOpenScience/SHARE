import logging
import random

import celery

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db import transaction
from django.utils import timezone

from share.change import ChangeGraph
from share.harvest.exceptions import HarvesterConcurrencyError
from share.harvest.scheduler import HarvestScheduler
from share.models import AbstractCreativeWork
from share.models import CeleryTaskResult
from share.models import ChangeSet
from share.models import HarvestJob
from share.models import IngestJob
from share.models import NormalizedData
from share.models import Source
from share.models import SourceConfig
from share.regulate import Regulator
from share.search import SearchIndexer
from share.util import chunked
from share.util.source_stat import SourceStatus
from share.util.source_stat import OAISourceStatus


logger = logging.getLogger(__name__)


@celery.shared_task(bind=True, max_retries=5)
def disambiguate(self, normalized_id):
    normalized = NormalizedData.objects.select_related('source__source').get(pk=normalized_id)

    if self.request.id:
        self.update_state(meta={
            'source': normalized.source.source.long_title
        })

    updated = None

    try:
        # Load all relevant ContentTypes in a single query
        ContentType.objects.get_for_models(*apps.get_models('share'), for_concrete_models=False)

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
        jobs = []

        # TODO take harvest/sourceconfig version into account here
        for source_config in qs.exclude(harvester__isnull=True).select_related('harvester').annotate(latest=models.Max('harvestjobs__end_date')):
            jobs.extend(HarvestScheduler(source_config).all(cutoff=cutoff, save=False))

        HarvestJob.objects.bulk_get_or_create(jobs)


@celery.shared_task(bind=True, max_retries=5)
def harvest(self, **kwargs):
    """Complete the harvest of the given HarvestJob or next the next available HarvestJob.

    Args:
        job_id (int, optional): Harvest the given job. Defaults to None.
            If the given job cannot be locked, the task will retry indefinitely.
            If the given job belongs to a disabled or deleted Source or SourceConfig, the task will fail.
        exhaust (bool, optional): Whether or not to start another harvest task if one is found. Defaults to True.
            Used to prevent a backlog of harvests. If we have a valid job, spin off another task to eat through
            the rest of the queue.
        ignore_disabled (bool, optional):
        superfluous (bool, optional): Re-ingest Rawdata that we've already collected. Defaults to False.
        force (bool, optional)


        ingest (bool, optional): Whether or not to start the full ingest process for harvested data. Defaults to True.
        limit (int, optional)
    """
    HarvestJobConsumer(self, **kwargs).consume()


@celery.shared_task(bind=True, max_retries=5)
def ingest(self, **kwargs):
    IngestJobConsumer(self, **kwargs).consume()


class JobConsumer:
    def __init__(self, task, job_id=None, exhaust=True, ignore_disabled=False, superfluous=False, force=False):
        self.task = task
        self.job_id = job_id
        self.exhaust = exhaust
        self.ignore_disabled = ignore_disabled
        self.superfluous = superfluous
        self.force = force

    @property
    def job_class(self):
        raise NotImplementedError()

    @property
    def lock_field(self):
        raise NotImplementedError()

    @property
    def task_function(self):
        raise NotImplementedError()

    def _consume_job(self, job):
        raise NotImplementedError()

    def consume(self):
        with self._locked_job() as job:
            if job is None and self.job_id is None:
                logger.info('No %ss are currently available', self.job_class.__name__)
                return None

            if job is None and self.job_id is not None:
                # If an id was given to us, we should have gotten a job
                job = self.job_class.objects.get(id=self.job_id)  # Force the failure
                raise Exception('Failed to load {} but then found {!r}.'.format(self.job_id, job))  # Should never be reached

            if self.task.request.id:
                # Additional attributes for the celery backend
                # Allows for better analytics of currently running tasks
                self.task.update_state(meta={
                    'job_id': job.id,
                    'source': job.source_config.source.long_title,
                    'source_config': job.source_config.label,
                })

                job.task_id = self.task.request.id
                self.job_class.objects.filter(id=job.id).update(task_id=self.task.request.id)

            if job.completions > 0 and job.status == self.job_class.STATUS.succeeded:
                if not self.superfluous:
                    job.skip(self.job_class.SkipReasons.duplicated)
                    logger.warning('%r has already been harvested. Force a re-run with superfluous=True', job)
                    return None
                logger.info('%r has already been harvested. Re-running superfluously', job)

            if self.exhaust and self.job_id is None:
                if self.force:
                    logger.warning('propagating force=True until queue exhaustion')

                logger.debug('Spawning another task to consume %s', self.job_class.__name__)
                res = self.task_function.apply_async(self.task.request.args, self.task.request.kwargs)
                logger.info('Spawned %r', res)

            if not job.update_versions():
                job.skip(self.job_class.SkipReasons.obsolete)
                return

            logger.info('Consuming %r', job)
            with job.handle():
                self._consume_job(job)

    def _filter_ready(self, qs):
        return qs.filter(
            status__in=self.job_class.READY_STATUSES
        )

    def _locked_job(self):
        qs = self.job_class.objects.all()
        if self.job_id is not None:
            logger.debug('Loading %s %d', self.job_class.__name__, self.job_id)
            qs = qs.filter(id=self.job_id)
        else:
            logger.debug('job_id was not specified, searching for an available job.')

            if not self.ignore_disabled:
                qs = qs.exclude(
                    source_config__disabled=True,
                ).exclude(
                    source_config__source__is_deleted=True
                )
            qs = self._filter_ready(qs).unlocked(self.lock_field)

        return qs.lock_first(self.lock_field)


class HarvestJobConsumer(JobConsumer):
    job_class = HarvestJob
    lock_field = 'source_config'
    task_function = harvest

    def __init__(self, *args, limit=None, ingest=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.ingest = ingest
        self.limit = limit

    def _filter_ready(self, qs):
        qs = super()._filter_ready(qs)
        return qs.filter(
            end_date__lte=timezone.now().date(),
            source_config__harvest_after__lte=timezone.now().time(),
        )

    def _consume_job(self, job):
        try:
            if self.ingest:
                datum_gen = (datum for datum in self._harvest(job) if datum.created or self.superfluous)
                for chunk in chunked(datum_gen, 500):
                    self._bulk_schedule_ingest(job, chunk)
            else:
                for _ in self._harvest(job):
                    pass
        except HarvesterConcurrencyError as e:
            # If job_id was specified there's a chance that the advisory lock was not, in fact, acquired.
            # If so, retry indefinitely to preserve existing functionality.
            # Use random to add jitter to help break up locking issues
            # Kinda hacky, allow a stupidly large number of retries as there is no options for infinite
            raise self.task.retry(
                exc=e,
                max_retries=99999,
                countdown=(random.random() + 1) * min(settings.CELERY_RETRY_BACKOFF_BASE ** self.task.request.retries, 60 * 15)
            )

    def _harvest(self, job):
        error = None
        datum_ids = []
        logger.info('Harvesting %r', job)
        harvester = job.source_config.get_harvester()

        try:
            for datum in harvester.harvest_date_range(job.start_date, job.end_date, limit=self.limit, force=self.force):
                datum_ids.append(datum.id)
                yield datum
        except Exception as e:
            error = e
            raise error
        finally:
            try:
                job.raw_data.add(*datum_ids)
            except Exception as e:
                logger.exception('Failed to connect %r to raw data', job)
                # Avoid shadowing the original error
                if not error:
                    raise e

    def _bulk_schedule_ingest(self, job, datums):
        job_kwargs = {
            'source_config': job.source_config,
            'source_config_version': job.source_config.version,
            'transformer_version': job.source_config.transformer.version,
            'regulator_version': Regulator.VERSION,
        }
        IngestJob.objects.bulk_get_or_create(
            [IngestJob(raw_id=datum.id, suid_id=datum.suid_id, **job_kwargs) for datum in datums]
        )


class IngestJobConsumer(JobConsumer):
    job_class = IngestJob
    lock_field = 'suid'
    task_function = ingest

    def _consume_job(self, job):
        # TODO think about getting rid of these triangles
        assert job.suid_id == job.raw.suid_id
        assert job.source_config_id == job.suid.source_config_id

        if self.job_class.objects.filter(status__in=job.READY_STATUSES, suid=job.suid, raw__datestamp__gt=job.raw.datestamp).exists():
            job.skip(job.SkipReasons.pointless)

        transformer = job.suid.source_config.get_transformer()
        graph = transformer.transform(job.raw)
        job.log_graph('transformed_data', graph)

        if not graph:
            if not raw.normalizeddata_set.exists():
                logger.warning('Graph was empty for %s, setting no_output to True', raw)
                RawDatum.objects.filter(id=raw_id).update(no_output=True)
            else:
                logger.warning('Graph was empty for %s, but a normalized data already exists for it', raw)
            return

        Regulator(job).regulate(graph)
        job.log_graph('regulated_data', graph)

        # TODO save as unmerged single-source graph

        if settings.SHARE_LEGACY_PIPELINE:
            nd = NormalizedData.objects.create(
                data={'@graph': job.regulated_data},
                source=job.suid.source_config.source.user,
                raw=job.raw,
            )
            nd.tasks.add(CeleryTaskResult.objects.get(task_id=self.task.request.id))

            disambiguate.apply_async((nd.id,))


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
