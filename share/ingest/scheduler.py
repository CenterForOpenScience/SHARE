from django.db import transaction

from share.models import IngestJob
from share.tasks import ingest
from share.tasks.jobs import IngestJobConsumer


class IngestScheduler:
    """Utility class for creating IngestJobs
    """

    @transaction.atomic
    def schedule(self, suid, superfluous=False, claim=False):
        """Get or create an IngestJob for the given suid.

        Params:
            suid: SourceUniqueIdentifier instance to ingest
            superfluous: If the job already exists and has completed, re-enqueue it.
            claim: Prevent the regularly scheduled `ingest` task from choosing this job.
        """
        job = suid.ingest_job
        created = False
        if job is None:
            job, created = IngestJob.objects.get_or_create(
                suid=suid,
                defaults={
                    'claimed': claim,
                    'source_config': suid.source_config,
                },
            )
        if not created:
            job.claimed = claim
            if superfluous and job.status not in IngestJob.READY_STATUSES:
                job.status = IngestJob.STATUS.created
            job.save(update_fields=('status', 'claimed'))
        return job

    def bulk_schedule(self, suid_qs, superfluous=False, claim=False):
        qs = suid_qs.select_related('source_config')

        def job_kwargs(suid):
            kwargs = {
                'suid': suid,
                'claimed': claim,
            }
            if superfluous:
                kwargs['status'] = IngestJob.STATUS.created
            return kwargs

        job_gen = (
            IngestJob(**job_kwargs(suid))
            for suid in qs.iterator()
        )

        return IngestJob.objects.bulk_get_or_create(
            job_gen,
            update_fields=['claimed', 'status'] if superfluous else ['claimed'],
        )

    def reingest(self, suid):
        """Synchronously reingest the given suid.
        """
        job = self.schedule(suid, superfluous=True, claim=True)
        IngestJobConsumer().consume(**self._reingest_kwargs(job))
        return job

    def reingest_async(self, suid):
        """Create an IngestJob for the given suid, and an `ingest` task assigned to it.
        """
        job = self.schedule(suid, superfluous=True, claim=True)
        ingest.delay(**self._reingest_kwargs(job))
        return job

    def bulk_reingest(self, suid_qs):
        """Create IngestJobs and `ingest` tasks for all suids in the given queryset
        """
        jobs = self.bulk_schedule(suid_qs, superfluous=True, claim=True)

        for job in jobs:
            ingest.delay(**self._reingest_kwargs(job))

        return jobs

    def _reingest_kwargs(self, job):
        return {
            'job_id': job.id,
            'exhaust': False,
            'superfluous': True,
        }
