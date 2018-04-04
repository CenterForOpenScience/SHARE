import os

from pprint import pprint

from share.bin.util import command
from share.ingest.scheduler import IngestScheduler
from share.models import SourceConfig, RawDatum, SourceUniqueIdentifier


@command('Run a SourceConfig\'s transformer')
def transform(args, argv):
    """
    Usage: {0} transform <sourceconfig> FILE ...
           {0} transform <sourceconfig> --directory=DIR
           {0} transform --ids <raw_data_ids>...

    Options:
        -d, --directory=DIR  Transform all JSON files in DIR
        -i, --ids            Provide RawDatum IDs to transform

    Transform all given JSON files. Results will be printed to stdout.
    """
    from ipdb import launch_ipdb_on_exception

    ids = args['<raw_data_ids>']
    if ids:
        qs = RawDatum.objects.filter(id__in=ids)
        for raw in qs.iterator():
            transformer = raw.suid.source_config.get_transformer()
            with launch_ipdb_on_exception():
                print('Parsed raw data "{}" into'.format(raw.id))
                pprint(transformer.transform(raw.datum))
                print('\n')
        return

    config = SourceConfig.objects.get(label=args['<sourceconfig>'])
    transformer = config.get_transformer()

    if args['FILE']:
        files = args['FILE']
    else:
        files = [os.path.join(args['--directory'], x) for x in os.listdir(args['--directory']) if not x.startswith('.')]

    for name in files:
        with open(name) as fobj:
            data = fobj.read()
        with launch_ipdb_on_exception():
            print('Parsed raw data "{}" into'.format(name))
            pprint(transformer.transform(data).to_jsonld(in_edges=False))
            print('\n')


@command('Create IngestJobs for the specified RawDatum(s)')
def ingest(args, argv):
    """
    Usage: {0} ingest <source_configs>... [--superfluous] [--now]
           {0} ingest --suids <suid_ids>... [--now]

    Options:
        -i, --suids         Provide Suid IDs to ingest specifically
        -s, --superfluous   Don't skip RawDatums that already have an IngestJob
        -n, --now           Run ingest tasks synchronously for each IngestJob
    """
    suid_ids = args['<suid_ids>']
    source_configs = args['<source_configs>']
    superfluous = args.get('<superfluous>')
    run_now = args['--now']

    qs = SourceUniqueIdentifier.objects.all()
    if suid_ids:
        qs = qs.filter(id__in=suid_ids)
    elif source_configs:
        qs = qs.filter(source_config__label__in=source_configs)
    else:
        raise ValueError('Need raw ids, suid ids, or source configs')

    if not superfluous:
        qs = qs.filter(ingest_jobs=None)

    scheduler = IngestScheduler()
    if run_now:
        for suid in qs:
            print('Ingesting {!r}...'.format(suid))
            scheduler.reingest(suid)
    else:
        jobs = scheduler.bulk_reingest(qs)
        print('Scheduled {} IngestJobs'.format(len(jobs)))
