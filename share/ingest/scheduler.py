from django.db import transaction
from django.db.models import Subquery, OuterRef
from django.db.models.functions import Coalesce

from share.models import IngestJob, RawDatum
from share.regulate import Regulator
from share.tasks import ingest
from share.tasks.jobs import IngestJobConsumer


class IngestScheduler:
    """Utility class for creating IngestJobs
    """

    @transaction.atomic
    def schedule(self, suid, raw_id=None, superfluous=False, claim=False):
        """Get or create an IngestJob for the given suid.

        Params:
            raw_id: ID for the specific raw datum to ingest. If omitted, uses the most recent.
            superfluous: If the job already exists and has completed, re-enqueue it.
            claim: Prevent the regularly scheduled `ingest` task from choosing this job.
        """
        if raw_id is None:
            raw_id = self._last_raw_qs(suid).first()

        job, created = IngestJob.objects.get_or_create(
            raw_id=raw_id,
            source_config_version=suid.source_config.version,
            transformer_version=suid.source_config.transformer.version,
            regulator_version=Regulator.VERSION,
            defaults={
                'claimed': claim,
                'suid': suid,
                'source_config': suid.source_config,
            },
        )
        if not created:
            job.claimed = claim
            if superfluous and job.status not in IngestJob.READY_STATUSES:
                job.status = IngestJob.STATUS.created
            job.save(update_fields=('status', 'claimed'))
        return job

    def reingest(self, suid):
        """Synchronously reingest the given suid.
        """
        job = self.schedule(suid, superfluous=True, claim=True)
        IngestJobConsumer().consume(**self._ingest_kwargs(job))
        return job

    def reingest_async(self, suid):
        """Create an IngestJob for the given suid, and an `ingest` task assigned to it.
        """
        job = self.schedule(suid, superfluous=True, claim=True)
        ingest.delay(**self._ingest_kwargs(job))
        return job

    def bulk_reingest(self, suid_qs):
        """Create IngestJobs and `ingest` tasks for all suids in the given queryset
        """
        qs = suid_qs.annotate(
            last_raw_id=Subquery(self._last_raw_qs(OuterRef('id')))
        ).select_related('source_config', 'source_config__transformer')

        job_gen = (
            IngestJob(
                raw_id=suid.last_raw_id,
                suid=suid,
                source_config=suid.source_config,
                claimed=True,
                source_config_version=suid.source_config.version,
                transformer_version=suid.source_config.transformer.version,
                regulator_version=Regulator.VERSION,
            )
            for suid in qs.iterator()
        )

        jobs = IngestJob.objects.bulk_get_or_create(
            job_gen,
            update_fields=['claimed'],
            defer_fields=['transformed_datum', 'regulated_datum'],
        )
        for job in jobs:
            ingest.delay(**self._ingest_kwargs(job))

        return jobs

    def _ingest_kwargs(self, job):
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
