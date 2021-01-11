from django.db import connection

from share.management.commands import BaseShareCommand
from share.models.jobs import IngestJob
from share.tasks import ingest
from share.util.extensions import Extensions


# get most recent job.id for each suid
# TODO clean up significantly once ingest jobs and suids are one-to-one
ingest_job_sql = '''
SELECT DISTINCT ON (job.suid_id) job.id, job.suid_id
FROM share_ingestjob AS job
WHERE job.suid_id >= %(suid_start_id)s
ORDER BY job.suid_id ASC, job.date_started DESC NULLS LAST, job.date_created DESC
'''


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

        # giving the cursor a name makes it a server-side cursor
        with connection._cursor(name='most_recent_job_per_suid') as cursor:
            cursor.execute(ingest_job_sql, {'suid_start_id': suid_start_id})
            while True:
                result_rows = cursor.fetchmany(size=2000)
                if not result_rows:
                    self.stdout.write('all done!')
                    break
                last_suid_id = result_rows[-1][1]
                job_ids = [result_row[0] for result_row in result_rows]
                IngestJob.objects.filter(id__in=job_ids).update(status=IngestJob.STATUS.created)
                for job_id in job_ids:
                    ingest.delay(
                        job_id=job_id,
                        apply_changes=False,  # skip the whole ShareObject mess
                        pls_format_metadata=True,
                        metadata_formats=metadata_formats,
                    )
                self.stdout.write(f'queued tasks for {len(job_ids)} IngestJobs (last suid: {last_suid_id})...')
