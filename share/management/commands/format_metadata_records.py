from django.db.models import Exists, OuterRef, Subquery
from django.db.models.functions import Coalesce

from share.tasks.scheduler import IngestScheduler
from share.management.commands import BaseShareCommand
from share.models.formatted_metadata_record import FormattedMetadataRecord
from share.models.ingest import SourceConfig, SourceUniqueIdentifier
from share.models.jobs import IngestJob
from share.tasks import ingest
from share.util.extensions import Extensions
from share.util.osf import osf_sources


CHUNK_SIZE = 2000


class Command(BaseShareCommand):
    def add_arguments(self, parser):
        parser.add_argument('metadata_formats', nargs='+', help='metadata format name (see entry points in setup.py)')

        source_config_group = parser.add_mutually_exclusive_group(required=True)
        source_config_group.add_argument('--source-config', '-c', action='append', help='format data from these source configs')
        source_config_group.add_argument('--osf-source-configs', '-o', action='store_true', help='format data from OSF source configs')
        source_config_group.add_argument('--all-source-configs', '-a', action='store_true', help='format data from *all* source configs')

        parser.add_argument('--suid-start-id', '-s', type=int, default=0, help='resume based on the previous run\'s last successful suid')
        parser.add_argument('--pls-ensure-ingest-jobs', '-j', action='store_true', help='before starting, ensure that all relevant suids have ingest jobs')
        parser.add_argument('--pls-reformat', '-r', action='store_true', help='re-format records that are already in these formats')
        parser.add_argument('--pls-reingest', '-i', action='store_true', help='re-ingest records from raw, ignoring old normalizeddata')

    def handle(self, *args, **options):
        metadata_formats = options['metadata_formats']
        suid_start_id = options['suid_start_id']
        pls_ensure_ingest_jobs = options['pls_ensure_ingest_jobs']
        pls_reformat = options['pls_reformat']
        pls_reingest = options['pls_reingest']

        valid_formats = Extensions.get_names('share.metadata_formats')
        if any(mf not in valid_formats for mf in metadata_formats):
            invalid_formats = set(metadata_formats).difference(valid_formats)
            self.stderr.write(f'Invalid metadata format(s): {invalid_formats}. Valid formats: {valid_formats}')
            return

        source_config_ids = self.get_source_config_ids(options)
        if not source_config_ids:
            return

        base_suid_qs = self._base_suid_qs(metadata_formats, source_config_ids, pls_reformat)

        if pls_ensure_ingest_jobs:
            self.ensure_ingest_jobs_exist(base_suid_qs)

        while True:
            last_successful_suid = self.enqueue_job_chunk(base_suid_qs, suid_start_id, metadata_formats, pls_reingest)
            if last_successful_suid is None:
                break
            suid_start_id = int(last_successful_suid) + 1

    def get_source_config_ids(self, options):
        source_config_labels = options['source_config']
        osf_source_configs = options['osf_source_configs']
        all_source_configs = options['all_source_configs']

        if all_source_configs:
            return tuple(SourceConfig.objects.filter(
                disabled=False,
                source__is_deleted=False,
            ).values_list('id', flat=True))

        if osf_source_configs:
            return tuple(SourceConfig.objects.filter(
                disabled=False,
                source__is_deleted=False,
                source__in=osf_sources(),
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

    def _base_suid_qs(self, metadata_formats, source_config_ids, pls_reformat):
        suid_qs = (
            SourceUniqueIdentifier.objects
            .filter(source_config__in=source_config_ids)
            .annotate(latest_ingest_job_id=Subquery(
                IngestJob.objects
                .filter(suid_id=OuterRef('id'))
                .order_by(Coalesce('date_started', 'date_created').desc(nulls_last=True))
                .values('id')
                [:1]
            ))
        )
        if not pls_reformat:
            fmr_exists_annotations = {
                f'fmr_exists_{metadata_format}': Exists(
                    FormattedMetadataRecord.objects.filter(
                        record_format=metadata_format,
                        suid_id=OuterRef('id'),
                    )
                )
                for metadata_format in metadata_formats
            }
            fmr_exists_for_all_formats = {
                fmr_exists: True
                for fmr_exists in fmr_exists_annotations.keys()
            }
            suid_qs = (
                suid_qs
                .annotate(**fmr_exists_annotations)
                .exclude(**fmr_exists_for_all_formats)
            )
        return suid_qs.order_by('id')

    def ensure_ingest_jobs_exist(self, base_suid_qs):
        unjobbed_suids = base_suid_qs.filter(latest_ingest_job_id=None)
        IngestScheduler().bulk_schedule(unjobbed_suids)

    def enqueue_job_chunk(self, base_suid_qs, suid_start_id, metadata_formats, pls_reingest):
        result_chunk = tuple(
            base_suid_qs
            .filter(id__gte=suid_start_id)
            .values('id', 'latest_ingest_job_id')
            [:CHUNK_SIZE]
        )

        if not result_chunk:
            self.stdout.write('all done!')
            return None

        last_suid_id = result_chunk[-1]['id']
        job_ids = tuple(result['latest_ingest_job_id'] for result in result_chunk)

        jobs_to_update = (
            IngestJob.objects
            .filter(id__in=job_ids)
            .exclude(status=IngestJob.STATUS.started)
        )
        jobs_to_update.update(status=IngestJob.STATUS.created)

        for job_id in job_ids:
            ingest.delay(
                job_id=job_id,
                superfluous=pls_reingest,  # whether to start from RawDatum or NormalizedDatum
                metadata_formats=metadata_formats,
            )
        self.stdout.write(f'queued tasks for {len(result_chunk)} IngestJobs (last suid: {last_suid_id})...')
        return last_suid_id
