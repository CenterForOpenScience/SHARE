import os

from pprint import pprint

from share import tasks
from share.bin.util import command
from share.models import SourceConfig, RawDatum, IngestJob
from share.regulate import Regulator


@command('Run a SourceConfig\'s transformer')
def transform(args, argv):
    """
    Usage: {0} transform [--regulate] <sourceconfig> FILE ...
           {0} transform [--regulate] <sourceconfig> --directory=DIR
           {0} transform [--regulate] --ids <raw_data_ids>...

    Options:
        -r, --regulate       Run the Regulator on the transformed graph
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
            graph = transformer.transform(data)
            if args.get('--regulate'):
                Regulator(source_config=config).regulate(graph)
            print('Parsed raw data "{}" into'.format(name))
            pprint(graph.to_jsonld(in_edges=False))
            print('\n')


@command('Create IngestJobs for the specified RawDatum(s)')
def ingest(args, argv):
    """
    Usage: {0} ingest (<source_configs>... | --all) [--superfluous] [--task | --run]
           {0} ingest --ids <raw_data_ids>... [--task | --run]

    Options:
        -i, --ids           Provide RawDatum IDs to ingest specifically
        -s, --superfluous   Reingest RawDatums that already have an IngestJob
        -t, --task          Spawn an ingest task after creating IngestJobs
        -r, --run           Run ingest tasks synchronously for each IngestJob
    """
    ids = args['<raw_data_ids>']
    source_configs = args['<source_configs>']
    superfluous = args.get('<superfluous>')

    qs = RawDatum.objects.all()
    if ids:
        qs = qs.filter(id__in=ids)
    else:
        if source_configs:
            qs = qs.filter(suid__source_config__label__in=source_configs)
        if not superfluous:
            qs = qs.filter(ingest_jobs=None)

    claim_jobs = args['--run'] or args['--task']

    count = 0
    jobs = []
    for raw in qs.iterator():
        count += 1
        jobs.append(IngestJob.schedule(raw, superfluous=superfluous, claim=claim_jobs))
    print('Scheduled {} IngestJobs'.format(count))

    if not claim_jobs:
        return

    kwargs = {
        'ignore_disabled': False,
    }
    for job in jobs:
        if args['--run']:
            tasks.ingest.apply((), {'job_id': job.id, **kwargs}, throw=True)
        elif args['--task']:
            tasks.ingest.apply_async((), {'job_id': job.id, **kwargs})
