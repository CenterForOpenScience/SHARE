from django.db import connection
from django.db.models import Exists, OuterRef

from share.ingest.scheduler import IngestScheduler
from share.management.commands import BaseShareCommand
from share.models.ingest import SourceConfig, SourceUniqueIdentifier
from share.models.jobs import IngestJob
from share.tasks import ingest
from share.util.extensions import Extensions


# find most recent job for each suid, set its status back to `created`,
# and return the job and suid ids
# TODO rewrite with django orm once ingest jobs and suids are one-to-one
update_ingest_job_sql = '''
WITH latest_job_per_suid AS (
    SELECT DISTINCT ON (latest_job.suid_id) latest_job.id
    FROM share_ingestjob AS latest_job
    JOIN share_sourceuniqueidentifier suid ON latest_job.suid_id = suid.id
    WHERE latest_job.suid_id >= %(suid_start_id)s AND suid.source_config_id IN %(source_config_ids)s
    ORDER BY latest_job.suid_id ASC, latest_job.date_started DESC NULLS LAST, latest_job.date_created DESC
    LIMIT %(chunk_size)s
)
UPDATE share_ingestjob AS job
SET status=%(set_job_status)s
FROM latest_job_per_suid
WHERE job.id = latest_job_per_suid.id AND job.status != %(in_progress_status)s
RETURNING job.id, job.suid_id
'''

CHUNK_SIZE = 2000


class Command(BaseShareCommand):
    def add_arguments(self, parser):
        parser.add_argument('metadata_formats', nargs='+', help='metadata format name (see entry points in setup.py)')
        parser.add_argument('--suid-start-id', '-s', type=int, default=0, help='resume based on the previous run\'s last successful suid')
        parser.add_argument('--ensure-ingest-jobs', '-j', action='store_true', help='before starting, ensure that all relevant suids have ingest jobs')
        source_config_group = parser.add_mutually_exclusive_group(required=True)
        source_config_group.add_argument('--source-config', '-c', action='append', help='format data from these source configs')
        source_config_group.add_argument('--all-source-configs', '-a', action='store_true', help='format data from *all* source configs')

    def handle(self, *args, **options):
        metadata_formats = options['metadata_formats']
        suid_start_id = options['suid_start_id']
        ensure_ingest_jobs = options['ensure_ingest_jobs']

        valid_formats = Extensions.get_names('share.metadata_formats')
        if any(mf not in valid_formats for mf in metadata_formats):
            invalid_formats = set(metadata_formats).difference(valid_formats)
            self.stderr.write(f'Invalid metadata format(s): {invalid_formats}. Valid formats: {valid_formats}')
            return

        source_config_ids = self.get_source_config_ids(options)
        if not source_config_ids:
            return

        if ensure_ingest_jobs:
            self.ensure_ingest_jobs_exist(source_config_ids)

        with connection.cursor() as cursor:
            while True:
                last_successful_suid = self.enqueue_job_chunk(cursor, suid_start_id, metadata_formats, source_config_ids)
                if last_successful_suid is None:
                    break
                suid_start_id = int(last_successful_suid) + 1

    def get_source_config_ids(self, options):
        source_config_labels = options['source_config']
        all_source_configs = options['all_source_configs']

        if all_source_configs:
            return tuple(SourceConfig.objects.filter(
                disabled=False,
                source__is_deleted=False,
            ).values_list('id', flat=True))

        ids_and_labels = SourceConfig.objects.filter(
            label__in=source_config_labels,
            source__is_deleted=False,
        ).values('id', 'label')

        given_labels = set(source_config_labels)
        valid_labels = set(il['label'] for il in ids_and_labels)
        if valid_labels != set(source_config_labels):
            self.stderr.write(f'Invalid source configs: {given_labels - valid_labels}')
            return None
        return tuple(il['id'] for il in ids_and_labels)

    def ensure_ingest_jobs_exist(self, source_config_ids):
        self.stdout.write(f'creating ingest jobs as needed for source configs {source_config_ids}...')
        unjobbed_suids = (
            SourceUniqueIdentifier.objects
            .filter(source_config__in=source_config_ids)
            .annotate(
                has_ingest_job=Exists(IngestJob.objects.filter(suid_id=OuterRef('id')))
            )
            .filter(has_ingest_job=False)
        )
        IngestScheduler().bulk_schedule(unjobbed_suids)

    def enqueue_job_chunk(self, cursor, suid_start_id, metadata_formats, source_config_ids):
        cursor.execute(update_ingest_job_sql, {
            'suid_start_id': suid_start_id or 0,
            'source_config_ids': source_config_ids,
            'chunk_size': CHUNK_SIZE,
            'set_job_status': IngestJob.STATUS.created,
            'in_progress_status': IngestJob.STATUS.started,
        })
        result_rows = cursor.fetchall()
        if not result_rows:
            self.stdout.write('all done!')
            return None

        last_suid_id = result_rows[-1][1]
        for result_row in result_rows:
            job_id = result_row[0]
            ingest.delay(
                job_id=job_id,
                apply_changes=False,  # skip the whole ShareObject mess
                pls_format_metadata=True,  # definitely don't skip this command's namesake
                metadata_formats=metadata_formats,
            )
        self.stdout.write(f'queued tasks for {len(result_rows)} IngestJobs (last suid: {last_suid_id})...')
        return last_suid_id
