import os

from pprint import pprint

from share.bin.util import command
from share.models import SourceConfig


@command('Run a SourceConfig\'s transformer')
def transform(args, argv):
    """
    Usage: {0} transform <sourceconfig> FILE ...
           {0} transform <sourceconfig> --directory=DIR

    Options:
        -d, --directory=DIR  Transform all JSON files in DIR

    Transform all given JSON files. Results will be printed to stdout.
    """
    config = SourceConfig.objects.get(label=args['<sourceconfig>'])
    transformer = config.get_transformer()

    if args['FILE']:
        files = args['FILE']
    else:
        files = [os.path.join(args['--directory'], x) for x in os.listdir(args['--directory']) if not x.startswith('.')]

    for name in files:
        with open(name) as fobj:
            data = fobj.read()
        from ipdb import launch_ipdb_on_exception
        with launch_ipdb_on_exception():
            print('Parsed raw data "{}" into'.format(name))
            pprint(transformer.transform(data))
            print('\n')
