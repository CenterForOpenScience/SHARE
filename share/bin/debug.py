from share.bin.util import command
from share.transform.chain import ctx


@command('Debug a SourceConfig\'s Transformer')
def debug(args, argv):
    """
    Usage: {0} debug <sourceconfig> FILE

    """
    from share.models import SourceConfig
    config = SourceConfig.objects.get(label=args['<sourceconfig>'])
    transformer = config.get_transformer()

    with open(args['FILE']) as fobj:
        data = transformer.unwrap_data(fobj.read())

    parser = transformer.get_root_parser(data)

    def execute(data, chain):
        return chain.chain()[0].run(data)
    e = execute  # noqa

    print('\n')
    print('ctx: {}'.format(ctx))
    print('parser: {}'.format(parser))
    print('data: {}'.format(type(data)))
    print('e, execute: {}'.format(execute))
    print('transformer: {}'.format(transformer))

    import ipdb
    ipdb.set_trace()
