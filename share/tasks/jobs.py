import logging
import random

from django.conf import settings
from django.utils import timezone

from share.exceptions import TransformError
from share.harvest.exceptions import HarvesterConcurrencyError
from share.models import CeleryTaskResult
from share.models import HarvestJob
from share.models import IngestJob
from share.models import NormalizedData
from share.models import RawDatum
from share.regulate import Regulator
from share.util import chunked


logger = logging.getLogger(__name__)


class JobConsumer:
    Job = None
    lock_field = None

    def __init__(self, task):
        if self.Job is None or self.lock_field is None:
            raise NotImplementedError
        self.task = task

    def _consume_job(self, job, **kwargs):
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
            if job is None and job_id is None:
                logger.info('No %ss are currently available', self.Job.__name__)
                return False

            if job is None and job_id is not None:
                # If an id was given to us, we should have gotten a job
                job = self.Job.objects.get(id=job_id)  # Force the failure
                raise Exception('Failed to load {} but then found {!r}.'.format(job_id, job))  # Should never be reached

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
        if self.task.request.id:
            # Additional attributes for the celery backend
            # Allows for better analytics of currently running tasks
            self.task.update_state(meta={
                'job_id': job.id,
                'source': job.source_config.source.long_title,
                'source_config': job.source_config.label,
            })

            job.task_id = self.task.request.id
            self.Job.objects.filter(id=job.id).update(task_id=self.task.request.id)

        if job.completions > 0 and job.status == self.Job.STATUS.succeeded:
            if not superfluous:
                job.skip(job.SkipReasons.duplicated)
                logger.warning('%r has already been consumed. Force a re-run with superfluous=True', job)
                return False
            logger.info('%r has already been consumed. Re-running superfluously', job)

        if not job.update_versions():
            job.skip(job.SkipReasons.obsolete)
            return False

        return True

    def _filter_ready(self, qs):
        return qs.filter(
            status__in=self.Job.READY_STATUSES
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


class HarvestJobConsumer(JobConsumer):
    Job = HarvestJob
    lock_field = 'source_config'

    def _filter_ready(self, qs):
        qs = super()._filter_ready(qs)
        return qs.filter(
            end_date__lte=timezone.now().date(),
            source_config__harvest_after__lte=timezone.now().time(),
        )

    def _consume_job(self, job, force, superfluous, limit=None, ingest=True, **kwargs):
        try:
            if ingest:
                datum_gen = (datum for datum in self._harvest(job, force, limit) if datum.created or superfluous)
                for chunk in chunked(datum_gen, 500):
                    self._bulk_schedule_ingest(job, chunk)
            else:
                for _ in self._harvest(job, force, limit):
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
    Job = IngestJob
    lock_field = 'suid'

    def _prepare_job(self, job, *args, **kwargs):
        # TODO think about getting rid of these triangles
        assert job.suid_id == job.raw.suid_id
        assert job.source_config_id == job.suid.source_config_id

        if self.Job.objects.filter(status__in=job.READY_STATUSES, suid=job.suid, raw__datestamp__gt=job.raw.datestamp).exists():
            job.skip(job.SkipReasons.pointless)
            return False

        return super()._prepare_job(job, *args, **kwargs)

    def _consume_job(self, job, **kwargs):
        transformer = job.suid.source_config.get_transformer()
        try:
            graph = transformer.transform(job.raw)
        except TransformError as e:
            job.fail(e)
            return

        job.log_graph('transformed_data', graph)

        if not graph:
            if not job.raw.normalizeddata_set.exists():
                logger.warning('Graph was empty for %s, setting no_output to True', job.raw)
                RawDatum.objects.filter(id=job.raw_id).update(no_output=True)
            else:
                logger.warning('Graph was empty for %s, but a normalized data already exists for it', job.raw)
            return

        Regulator(job).regulate(graph)
        job.log_graph('regulated_data', graph)

        # TODO save as unmerged single-source graph

        if settings.SHARE_LEGACY_PIPELINE:
            from share.tasks import disambiguate

            nd = NormalizedData.objects.create(
                data={'@graph': job.regulated_data},
                source=job.suid.source_config.source.user,
                raw=job.raw,
            )
            nd.tasks.add(CeleryTaskResult.objects.get(task_id=self.task.request.id))
            disambiguate.apply_async((nd.id,))
