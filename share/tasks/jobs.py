import logging
import random

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction, IntegrityError
from django.db.utils import OperationalError
from django.utils import timezone

from share import exceptions
from share.disambiguation import GraphDisambiguator
from share.harvest.exceptions import HarvesterConcurrencyError
from share.ingest.differ import NodeDiffer
from share.models import (
    AbstractCreativeWork,
    HarvestJob,
    IngestJob,
    NormalizedData,
    RawDatum,
)
from share.models.ingest import RawDatumJob
from share.regulate import Regulator
from share.search import SearchIndexer
from share.util import chunked


logger = logging.getLogger(__name__)


class JobConsumer:
    Job = None
    lock_field = None

    def __init__(self, task=None):
        if self.Job is None or self.lock_field is None:
            raise NotImplementedError
        self.task = task

    def _consume_job(self, job, **kwargs):
        raise NotImplementedError

    def _current_versions(self, job):
        """Get up-to-date values for the job's `*_version` fields

        Dict from field name to version number
        """
        raise NotImplementedError

    def consume(self, job_id=None, exhaust=True, ignore_disabled=False, superfluous=False, force=False, **kwargs):
        """Consume the given job, or consume an available job if no job is specified.

        Parameters:
            job_id (int, optional): Consume the given job. Defaults to None.
                If the given job cannot be locked, the task will retry indefinitely.
                If the given job belongs to a disabled or deleted Source or SourceConfig, the task will fail.
            exhaust (bool, optional): If True and there are queued jobs, start another task. Defaults to True.
                Used to prevent a backlog. If we have a valid job, spin off another task to eat through
                the rest of the queue.
            ignore_disabled (bool, optional): Consume jobs from disabled source configs and/or deleted sources. Defaults to False.
            superfluous (bool, optional): Re-ingest Rawdata that we've already collected. Defaults to False.
            force (bool, optional):
        Additional keyword arguments passed to _consume_job, along with superfluous and force
        """
        with self._locked_job(job_id, ignore_disabled) as job:
            if job is None:
                if job_id is None:
                    logger.info('No %ss are currently available', self.Job.__name__)
                    return
                else:
                    # If an id was given to us, we should have gotten a job
                    job = self.Job.objects.get(id=job_id)  # Force the failure
                    raise Exception('Failed to load {} but then found {!r}.'.format(job_id, job))  # Should never be reached

            assert self.task or not exhaust, 'Cannot pass exhaust=True unless running in an async context'
            if exhaust and job_id is None:
                if force:
                    logger.warning('propagating force=True until queue exhaustion')

                logger.debug('Spawning another task to consume %s', self.Job.__name__)
                res = self.task.apply_async(self.task.request.args, self.task.request.kwargs)
                logger.info('Spawned %r', res)

            if self._prepare_job(job, superfluous=superfluous):
                logger.info('Consuming %r', job)
                with job.handle():
                    self._consume_job(job, **kwargs, superfluous=superfluous, force=force)

    def _prepare_job(self, job, superfluous):
        if job.status == self.Job.STATUS.skipped:
            # Need some way to short-circuit a superfluous retry loop
            logger.warning('%r has been marked skipped. Change its status to allow re-running it', job)
            return False

        if self.task and self.task.request.id:
            # Additional attributes for the celery backend
            # Allows for better analytics of currently running tasks
            self.task.update_state(meta={
                'job_id': job.id,
                'source': job.source_config.source.long_title,
                'source_config': job.source_config.label,
            })

            job.task_id = self.task.request.id
            job.save(update_fields=('task_id',))

        if job.completions > 0 and job.status == self.Job.STATUS.succeeded:
            if not superfluous:
                job.skip(job.SkipReasons.duplicated)
                logger.warning('%r has already been consumed. Force a re-run with superfluous=True', job)
                return False
            logger.info('%r has already been consumed. Re-running superfluously', job)

        if not self._update_versions(job):
            job.skip(job.SkipReasons.obsolete)
            return False

        return True

    def _filter_ready(self, qs):
        return qs.filter(
            status__in=self.Job.READY_STATUSES,
        ).exclude(
            claimed=True
        )

    def _locked_job(self, job_id, ignore_disabled=False):
        qs = self.Job.objects.all()
        if job_id is not None:
            logger.debug('Loading %s %d', self.Job.__name__, job_id)
            qs = qs.filter(id=job_id)
        else:
            logger.debug('job_id was not specified, searching for an available job.')

            if not ignore_disabled:
                qs = qs.exclude(
                    source_config__disabled=True,
                ).exclude(
                    source_config__source__is_deleted=True
                )
            qs = self._filter_ready(qs).unlocked(self.lock_field)

        return qs.lock_first(self.lock_field)

    def _update_versions(self, job):
        """Update version fields to the values from self.current_versions

        Return True if successful, else False.
        """
        current_versions = self._current_versions(job)
        if all(getattr(job, f) == v for f, v in current_versions.items()):
            # No updates required
            return True

        if job.completions > 0:
            logger.warning('%r is outdated but has previously completed, skipping...', job)
            return False

        try:
            with transaction.atomic():
                for f, v in current_versions.items():
                    setattr(job, f, v)
                job.save()
            logger.warning('%r has been updated to the versions: %s', job, current_versions)
            return True
        except IntegrityError:
            logger.warning('A newer version of %r already exists, skipping...', job)
            return False


class HarvestJobConsumer(JobConsumer):
    Job = HarvestJob
    lock_field = 'source_config'

    def _filter_ready(self, qs):
        qs = super()._filter_ready(qs)
        return qs.filter(
            end_date__lte=timezone.now().date(),
            source_config__harvest_after__lte=timezone.now().time(),
        )

    def _current_versions(self, job):
        return {
            'source_config_version': job.source_config.version,
            'harvester_version': job.source_config.harvester.version,
        }

    def _consume_job(self, job, force, superfluous, limit=None, ingest=True):
        try:
            if ingest:
                datum_gen = (datum for datum in self._harvest(job, force, limit) if datum.created or superfluous)
                for chunk in chunked(datum_gen, 500):
                    self._bulk_schedule_ingest(job, chunk)
            else:
                for _ in self._harvest(job, force, limit):
                    pass
        except HarvesterConcurrencyError as e:
            if not self.task:
                raise
            # If job_id was specified there's a chance that the advisory lock was not, in fact, acquired.
            # If so, retry indefinitely to preserve existing functionality.
            # Use random to add jitter to help break up locking issues
            # Kinda hacky, allow a stupidly large number of retries as there is no options for infinite
            raise self.task.retry(
                exc=e,
                max_retries=99999,
                countdown=(random.random() + 1) * min(settings.CELERY_RETRY_BACKOFF_BASE ** self.task.request.retries, 60 * 15)
            )

    def _harvest(self, job, force, limit):
        error = None
        datum_ids = []
        logger.info('Harvesting %r', job)
        harvester = job.source_config.get_harvester()

        try:
            for datum in harvester.harvest_date_range(job.start_date, job.end_date, limit=limit, force=force):
                datum_ids.append(datum.id)
                yield datum
        except Exception as e:
            error = e
            raise error
        finally:
            try:
                RawDatumJob.objects.bulk_create([
                    RawDatumJob(job=job, datum_id=datum_id)
                    for datum_id in datum_ids
                ])
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
    Job = IngestJob
    lock_field = 'suid'

    MAX_RETRIES = 5

    def _current_versions(self, job):
        return {
            'source_config_version': job.source_config.version,
            'transformer_version': job.source_config.transformer.version,
            'regulator_version': Regulator.VERSION,
        }

    def _prepare_job(self, job, *args, **kwargs):
        # TODO think about getting rid of these triangles -- infer source config from suid?
        assert job.suid_id == job.raw.suid_id
        assert job.source_config_id == job.suid.source_config_id

        if job.raw.datestamp and self.Job.objects.filter(
                status__in=job.READY_STATUSES,
                suid=job.suid,
                raw__datestamp__gt=job.raw.datestamp
        ).exists():
            job.skip(job.SkipReasons.pointless)
            return False

        return super()._prepare_job(job, *args, **kwargs)

    def _consume_job(self, job, superfluous, force, apply_changes=True, index=True, urgent=False):
        datum = None

        # Check whether we've already done transform/regulate
        if not superfluous:
            datum = job.ingested_normalized_data.order_by('-created_at').first()

        if superfluous or datum is None:
            graph = self._transform(job)
            if not graph:
                return
            graph = self._regulate(job, graph)
            if not graph:
                return
            datum = NormalizedData.objects.create(
                data={'@graph': graph.to_jsonld()},
                source=job.suid.source_config.source.user,
                raw=job.raw,
            )
            job.ingested_normalized_data.add(datum)

        if apply_changes:
            updated_work_ids = self._apply_changes(job, graph, datum)
            if index and updated_work_ids:
                self._update_index(updated_work_ids, urgent)

    def _transform(self, job):
        transformer = job.suid.source_config.get_transformer()
        try:
            graph = transformer.transform(job.raw)
        except exceptions.TransformError as e:
            job.fail(e)
            return None

        if not graph:
            if not job.raw.normalizeddata_set.exists():
                logger.warning('Graph was empty for %s, setting no_output to True', job.raw)
                RawDatum.objects.filter(id=job.raw_id).update(no_output=True)
            else:
                logger.warning('Graph was empty for %s, but a normalized data already exists for it', job.raw)
            return None

        return graph

    def _regulate(self, job, graph):
        try:
            Regulator(job).regulate(graph)
            return graph
        except exceptions.RegulateError as e:
            job.fail(e)
            return None

    def _apply_changes(self, job, graph, normalized_datum):
        updated = None
        instance_map = None

        try:
            # Load all relevant ContentTypes in a single query
            ContentType.objects.get_for_models(*apps.get_models('share'), for_concrete_models=False)

            with transaction.atomic():
                user = normalized_datum.source  # "source" here is a user...
                source = user.source
                instance_map = GraphDisambiguator(source).find_instances(graph)
                change_set = NodeDiffer.build_change_set(graph, normalized_datum, instance_map)

                if change_set and (source or user.is_robot or user.is_trusted):
                    updated = change_set.accept()

        # Retry if it was just the wrong place at the wrong time
        except (exceptions.IngestConflict, OperationalError) as e:
            job.retries = (job.retries or 0) + 1
            job.save(update_fields=('retries',))
            if job.retries > self.MAX_RETRIES:
                raise
            job.reschedule()
            return

        if not updated:
            return  # Nothing to index

        # Index works that were added or directly updated
        updated_works = set(
            x.id
            for x in updated
            if isinstance(x, AbstractCreativeWork)
        )
        # and works that matched, even if they didn't change, in case any related objects did
        existing_works = set(
            x.id
            for x in (instance_map or {}).values()
            if isinstance(x, AbstractCreativeWork)
        )

        return list(updated_works | existing_works)

    def _update_index(self, work_ids, urgent):
        indexer = SearchIndexer(self.task.app) if self.task else SearchIndexer()
        indexer.index('creativework', *work_ids, urgent=urgent)
