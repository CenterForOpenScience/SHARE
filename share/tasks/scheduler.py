from django.db import transaction
from django.db.models import Subquery, OuterRef
from django.db.models.functions import Coalesce

from share.models import IngestJob, RawDatum
from share.legacy_normalize.regulate import Regulator
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
            superfluous: If the suid's latest datum has already been ingested, re-ingest it anyway.
            claim:
        """
        job, created = IngestJob.objects.get_or_create(
            suid=suid,
            defaults={
                'claimed': True,
            },
        )
        if not created and not job.claimed:
            job.claimed = True
            if job.status not in IngestJob.READY_STATUSES:
                job.status = IngestJob.STATUS.created
            job.save(update_fields=('status', 'claimed'))
        if not claim:
            ingest.delay(job_id=job.id, superfluous=superfluous, urgent=True)
        return job

    def bulk_schedule(self, suid_qs, superfluous=False, claim=False):
        qs = suid_qs.annotate(
            last_raw_id=Subquery(self._last_raw_qs(OuterRef('id')))
        ).select_related('source_config', 'source_config__transformer')

        def job_kwargs(suid):
            kwargs = {
                'raw_id': suid.last_raw_id,
                'suid': suid,
                'source_config': suid.source_config,
                'claimed': claim,
                'source_config_version': suid.source_config.version,
                'transformer_version': suid.source_config.transformer.version,
                'regulator_version': Regulator.VERSION,
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

    def _last_raw_qs(self, suid_q):
        return RawDatum.objects.filter(
            suid=suid_q
        ).order_by(
            Coalesce('datestamp', 'date_created').desc(nulls_last=True)
        ).values_list('id', flat=True)[:1]
