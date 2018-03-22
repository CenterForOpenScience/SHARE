from django.db import transaction
from django.db.models.functions import Coalesce

from share.models import IngestJob
from share.regulate import Regulator
from share.tasks import ingest
from share.tasks.jobs import IngestJobConsumer


class IngestScheduler:
    """Utility class for creating IngestJobs
    """

    @transaction.atomic
    def schedule(self, raw, superfluous=False, claim=False):
        job, created = IngestJob.objects.get_or_create(
            raw=raw,
            source_config_version=raw.suid.source_config.version,
            transformer_version=raw.suid.source_config.transformer.version,
            regulator_version=Regulator.VERSION,
            defaults={
                'claimed': claim,
                'suid': raw.suid,
                'source_config': raw.suid.source_config,
            },
        )
        if not created:
            job.claimed = claim
            if superfluous and job.status not in IngestJob.READY_STATUSES:
                job.status = IngestJob.STATUS.created
            job.save(update_fields=('status', 'claimed'))
        return job

    def reingest(self, suid, async=True):
        raw = suid.raw_data.order_by(Coalesce('datestamp', 'date_created').desc(nulls_last=True)).first()
        job = self.schedule(raw, superfluous=True, claim=True)
        kwargs = {
            'job_id': job.id,
            'exhaust': False,
            'superfluous': True,
        }
        if async:
            ingest.delay(**kwargs)
        else:
            IngestJobConsumer().consume(**kwargs)
        return job

    def bulk_reingest(self, suid_qs):
        # TODO optimize for bulk
        for suid in suid_qs:
            self.reingest(suid)
