from share.models import IngestJob
from share.regulate import Regulator


class IngestScheduler:
    """Utility class for creating IngestJobs
    """

    def schedule(self, raw, superfluous=False, claim=False):
        job, _ = IngestJob.objects.get_or_create(
            raw=raw,
            suid=raw.suid,
            source_config=raw.suid.source_config,
            source_config_version=raw.suid.source_config.version,
            transformer_version=raw.suid.source_config.transformer.version,
            regulator_version=Regulator.VERSION,
            claimed=claim,
        )
        if superfluous and job.status not in IngestJob.READY_STATUSES:
            job.status = IngestJob.STATUS.created
            job.save(update_fields=('status',))
        return job
