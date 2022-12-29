from share.bin.util import command
from share.tasks.scheduler import IngestScheduler
from share.models import SourceUniqueIdentifier
from share.models.jobs import IngestJob
from share.tasks import ingest as ingest_task
from share.util.osf import osf_sources


@command('Create IngestJobs for the specified RawDatum(s)')
def ingest(args, argv):
    """
    Usage: {0} ingest <source_configs>... [--superfluous] [--now]
           {0} ingest --suids <suid_ids>... [--superfluous] [--now]
           {0} ingest --osf [--superfluous] [--now]

    Options:
        -i, --suids         Provide Suid IDs to ingest specifically
        --osf               Shorthand for all source configs belonging to OSF sources
        -s, --superfluous   Don't skip RawDatums that already have an IngestJob
        -n, --now           Run ingest tasks synchronously for each IngestJob
    """
    suid_ids = args['<suid_ids>']
    source_configs = args['<source_configs>']
    superfluous = args.get('--superfluous')
    run_now = args['--now']
    osf = args['--osf']

    qs = SourceUniqueIdentifier.objects.all()
    if suid_ids:
        qs = qs.filter(id__in=suid_ids)
    elif source_configs:
        qs = qs.filter(source_config__label__in=source_configs)
    elif osf:
        qs = qs.filter(source_config__source__in=osf_sources())
    else:
        raise ValueError('Need raw ids, suid ids, or source configs')

    scheduler = IngestScheduler()
    if run_now:
        for suid in qs:
            print('Ingesting {!r}...'.format(suid))
            scheduler.reingest(suid)
    else:
        jobs = scheduler.bulk_reingest(qs)
        print('Scheduled {} IngestJobs'.format(len(jobs)))


@command('Put IngestJobs back in the worker queue')
def enqueue_ingest(args, argv):
    """
    Usage: {0} enqueue_ingest <job_ids>...
           {0} enqueue_ingest --all-of-status <job_statuses>...

    Options:
        -s, --all-of-status   Enqueue and start tasks for all jobs of the given statuses (e.g. created, failed)
    """
    job_ids = args.get('<job_ids>')

    if not job_ids:
        job_statuses = args.get('<job_statuses>')
        if not job_statuses:
            return
        status_values = [
            getattr(IngestJob.STATUS, status_key)
            for status_key in job_statuses
        ]
        job_ids = list(
            IngestJob.objects.filter(status__in=status_values).values_list('id', flat=True)
        )

    print(f're-enqueuing {len(job_ids)} jobs...')
    job_qs = IngestJob.objects.filter(id__in=job_ids)
    job_qs.update(status=IngestJob.STATUS.created)
    for job_id in job_ids:
        ingest_task.delay(job_id=job_id)
