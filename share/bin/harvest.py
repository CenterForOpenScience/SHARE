import re
import os

import pendulum

from share import tasks
from share.bin.util import command
from share.harvest.scheduler import HarvestScheduler
from share.models import SourceConfig


def get_sourceconfig(name):
    try:
        return SourceConfig.objects.get(label=name)
    except SourceConfig.DoesNotExist:
        print('SourceConfig "{}" not found.'.format(name))
        fuzzy = list(SourceConfig.objects.filter(label__icontains=name).values_list('label', flat=True))
        if fuzzy:
            print('Did you mean?\n\t{}'.format('\n\t'.join(fuzzy)))
    return None


@command('Fetch data to disk or stdout, using the specified SourceConfig')
def fetch(args, argv):
    """
    Usage:
        {0} fetch <sourceconfig> [<date> | --start=YYYY-MM-DD --end=YYYY-MM-DD] [--limit=LIMIT] [--print | --out=DIR] [--set-spec=SET]
        {0} fetch <sourceconfig> --ids <ids>... [--print | --out=DIR]

    Options:
        -l, --limit=NUMBER      Limit the harvester to NUMBER of documents
        -p, --print             Print results to stdout rather than to a file
        -o, --out=DIR           The directory to store the fetched data in. Defaults to ./fetched/<sourceconfig>
        -s, --start=YYYY-MM-DD  The date at which to start fetching data.
        -e, --end=YYYY-MM-DD    The date at which to stop fetching data.
        --set-spec=SET          The OAI setSpec to limit harvesting to.
        --ids                   IDs of specific records to fetch.
    """
    config = get_sourceconfig(args['<sourceconfig>'])
    if not config:
        return -1

    harvester = config.get_harvester(pretty=True)

    ids = args['<ids>']
    if ids:
        gen = (harvester.fetch_by_id(id) for id in ids)
    else:
        kwargs = {k: v for k, v in {
            'limit': int(args['--limit']) if args.get('--limit') else None,
            'set_spec': args.get('--set-spec'),
        }.items() if v is not None}

        if not args['<date>'] and not (args['--start'] and args['--end']):
            gen = harvester.fetch(**kwargs)
        elif args['<date>']:
            gen = harvester.fetch_date(pendulum.parse(args['<date>']), **kwargs)
        else:
            gen = harvester.fetch_date_range(pendulum.parse(args['--start']), pendulum.parse(args['--end']), **kwargs)

    if not args['--print']:
        args['--out'] = args['--out'] or os.path.join(os.curdir, 'fetched', config.label)
        os.makedirs(args['--out'], exist_ok=True)

    for result in gen:
        if args['--print']:
            print('Harvested data with identifier "{}"'.format(result.identifier))
            print(result.datum)
            print('\n')
        else:
            suffix = '.xml' if result.datum.startswith('<') else '.json'
            with open(os.path.join(args['--out'], re.sub(r'[:\\\/\?\*]', '', str(result.identifier))) + suffix, 'w') as fobj:
                fobj.write(result.datum)


@command('Harvest data using the specified SourceConfig')
def harvest(args, argv):
    """
    Usage:
        {0} harvest <sourceconfig> [<date>] [options]
        {0} harvest <sourceconfig> [<date>] [options]
        {0} harvest <sourceconfig> --all [<date>] [options]
        {0} harvest <sourceconfig> (--start=YYYY-MM-DD --end=YYYY-MM-DD) [options]

    Options:
        -l, --limit=NUMBER      Limit the harvester to NUMBER of documents
        -s, --start=YYYY-MM-DD  The date at which to start fetching data.
        -e, --end=YYYY-MM-DD    The date at which to stop fetching data.
        -q, --quiet             Do not print out the harvested records
        --set-spec=SET          The OAI setSpec to limit harvesting to.
    """
    config = get_sourceconfig(args['<sourceconfig>'])
    if not config:
        return -1

    kwargs = {k: v for k, v in {
        'limit': int(args['--limit']) if args.get('--limit') else None,
        'set_spec': args.get('--set-spec'),
    }.items() if v is not None}

    if not args['<date>'] and not (args['--start'] and args['--end']):
        gen = config.get_harvester().harvest(**kwargs)
    elif args['<date>']:
        gen = config.get_harvester().harvest_date(pendulum.parse(args['<date>']), **kwargs)
    else:
        gen = config.get_harvester().harvest_date_range(pendulum.parse(args['--start']), pendulum.parse(args['--end']), **kwargs)

    # "Spin" the generator but don't keep the documents in memory
    for datum in gen:
        if args['--quiet']:
            continue
        print(datum)


@command('Create HarvestJobs for the specified SourceConfig')
def schedule(args, argv):
    """
    Usage:
        {0} schedule <sourceconfig> [<date> | (--start=YYYY-MM-DD --end=YYYY-MM-DD) | --complete] [--tasks | --run]
        {0} schedule [<date> | (--start=YYYY-MM-DD --end=YYYY-MM-DD) | --complete] [--tasks | --run] --all

    Options:
        -t, --tasks             Spawn harvest tasks for each created job.
        -r, --run               Run the harvest task for each created job.
        -a, --all               Schedule jobs for all enabled SourceConfigs.
        -c, --complete          Schedule all jobs between today and the SourceConfig's earliest date.
        -s, --start=YYYY-MM-DD  The date at which to start fetching data.
        -e, --end=YYYY-MM-DD    The date at which to stop fetching data.
        -j, --no-ingest         Do not process harvested data.
    """
    if not args['--all']:
        configs = [get_sourceconfig(args['<sourceconfig>'])]
        if not configs[0]:
            return -1
    else:
        configs = SourceConfig.objects.exclude(disabled=True).exclude(source__is_deleted=True)

    kwargs = {k: v for k, v in {
        'ingest': not args.get('--no-ingest'),
    }.items() if v is not None}

    claim_jobs = args['--run'] or args['--tasks']

    jobs = []
    for config in configs:
        scheduler = HarvestScheduler(config, claim_jobs=claim_jobs)

        if not (args['<date>'] or args['--start'] or args['--end']):
            jobs.append(scheduler.today())
        elif args['<date>']:
            jobs.append(scheduler.date(pendulum.parse(args['<date>'])))
        else:
            jobs.extend(scheduler.range(pendulum.parse(args['--start']), pendulum.parse(args['--end'])))

    if not claim_jobs:
        return

    for job in jobs:
        if args['--run']:
            tasks.harvest.apply((), {'job_id': job.id, **kwargs}, retry=False, throw=True)
        elif args['--tasks']:
            tasks.harvest.apply_async((), {'job_id': job.id, **kwargs})
