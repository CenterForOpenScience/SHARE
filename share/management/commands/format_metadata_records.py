from django.db import connection

from share.management.commands import BaseShareCommand
from share.models.jobs import IngestJob
from share.tasks import ingest
from share.util.extensions import Extensions


# find most recent job for each suid, set its status back to `created`,
# and return the job and suid ids
# TODO clean up significantly once ingest jobs and suids are one-to-one
update_ingest_job_sql = '''
WITH latest_job_per_suid AS (
    SELECT DISTINCT ON (latest_job.suid_id) latest_job.id
    FROM share_ingestjob AS latest_job
    WHERE latest_job.suid_id >= %(suid_start_id)s
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
        parser.add_argument('metadata_formats', nargs='*', help='metadata format name (see entry points in setup.py)')
        parser.add_argument('--suid-start-id', '-s', type=int, default=0, help='metadata format name (see entry points in setup.py)')

    def handle(self, *args, **options):
        metadata_formats = options['metadata_formats']
        suid_start_id = options['suid_start_id']

        valid_formats = Extensions.get_names('share.metadata_formats')
        if not metadata_formats:
            self.stdout.write(f'Valid metadata formats: {metadata_formats}')
            return
        if any(mf not in valid_formats for mf in metadata_formats):
            invalid_formats = set(metadata_formats).difference(valid_formats)
            self.stderr.write(f'Invalid metadata format(s): {invalid_formats}. Valid formats: {valid_formats}')
            return

        with connection.cursor() as cursor:
            while True:
                last_successful_suid = self.enqueue_job_chunk(cursor, suid_start_id, metadata_formats)
                if last_successful_suid is None:
                    break
                suid_start_id = int(last_successful_suid) + 1

    def enqueue_job_chunk(self, cursor, suid_start_id, metadata_formats):
        cursor.execute(update_ingest_job_sql, {
            'suid_start_id': suid_start_id or 0,
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
