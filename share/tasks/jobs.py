import logging
import random

from django.conf import settings
from django.db import transaction, IntegrityError
from django.utils import timezone

from share.harvest.exceptions import HarvesterConcurrencyError
from share.models import HarvestJob
from share.models.ingest import RawDatumJob
from share.util import chunked
from trove import digestive_tract


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

    def consume(self, job_id=None, exhaust=True, superfluous=False, **kwargs):
        """Consume the given job, or consume an available job if no job is specified.

        Parameters:
            job_id (int, optional): Consume the given job. Defaults to None.
                If the given job cannot be locked, the task will retry indefinitely.
                If the given job belongs to a disabled or deleted Source or SourceConfig, the task will fail.
            exhaust (bool, optional): If True and there are queued jobs, start another task. Defaults to True.
                Used to prevent a backlog. If we have a valid job, spin off another task to eat through
                the rest of the queue.
            superfluous (bool, optional): Consuming a job should be idempotent, and subsequent runs may
                skip doing work that has already been done. If superfluous=True, however, will do all
                work whether or not it's already been done. Default False.
        Additional keyword arguments passed to _consume_job, along with superfluous
        """
        with self._locked_job(job_id) as job:
            if job is None:
                if job_id is None:
                    logger.info('No %ss are currently available', self.Job.__name__)
                    return
                else:
                    message = f'Could not find/lock {self.Job.__name__}(id={job_id})'
                    logger.error(message)
                    raise self.Job.DoesNotExist(message)

            assert self.task or not exhaust, 'Cannot pass exhaust=True unless running in an async context'
            if exhaust and job_id is None:
                logger.debug('Spawning another task to consume %s', self.Job.__name__)
                res = self.task.apply_async(self.task.request.args, self.task.request.kwargs)
                logger.info('Spawned %r', res)

            if self._prepare_job(job, superfluous=superfluous):
                logger.info('Consuming %r', job)
                with job.handle():
                    self._consume_job(job, **kwargs, superfluous=superfluous)

    def _prepare_job(self, job, superfluous):
        if job.status == self.Job.STATUS.skipped:
            # Need some way to short-circuit a superfluous retry loop
            logger.warning('%r has been marked skipped. Change its status to allow re-running it', job)
            return False

        if self.task and self.task.request.id:
            # Additional attributes for the celery backend
            # Allows for better analytics of currently running tasks
            self.task.update_state(meta={'job_id': job.id})

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

    def _locked_job(self, job_id):
        qs = self.Job.objects.all()
        if job_id is not None:
            logger.debug('Loading %s %d', self.Job.__name__, job_id)
            qs = qs.filter(id=job_id)
        else:
            logger.debug('job_id was not specified, searching for an available job.')
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

    def _maybe_skip_by_source_config(self, job, source_config) -> bool:
        if source_config.disabled or source_config.source.is_deleted:
            job.skip(job.SkipReasons.disabled)
            return True
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
            'share_version': settings.VERSION,
            'source_config_version': job.source_config.version,
            'harvester_version': getattr(job.source_config.get_harvester(), 'VERSION', 1),
        }

    def _consume_job(self, job, superfluous, limit=None, ingest=True):
        if self._maybe_skip_by_source_config(job, job.source_config):
            return
        try:
            if ingest:
                datum_gen = (datum for datum in self._harvest(job, limit) if datum.created or superfluous)
                for chunk in chunked(datum_gen, 500):
                    self._bulk_schedule_ingest(job, chunk)
            else:
                for _ in self._harvest(job, limit):
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

    def _harvest(self, job, limit):
        error = None
        datum_ids = []
        logger.info('Harvesting %r', job)
        harvester = job.source_config.get_harvester()

        try:
            for datum in harvester.harvest_date_range(job.start_date, job.end_date, limit=limit):
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
        for _raw_datum in datums:
            digestive_tract.task__extract_and_derive.delay(raw_id=_raw_datum.id)
