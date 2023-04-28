from project.celery import app as celery_app

from share.bin.util import command
from share.search import IndexStrategy
from share.search.exceptions import IndexStrategyError
from share.search.daemon import IndexerDaemon


@command('Manage Elasticsearch')
def search(args, argv):
    """
    Usage:
        {0} search <command> [<args>...]

    Options:
        -h, --help           Show this screen.

    Commands:
    {1.subcommand_list}

    See '{0} search <command> --help' for more information on a specific command.
    """
    pass


@search.subcommand('Drop the Elasticsearch index')
def purge(args, argv):
    """
    Usage: {0} search purge <index_names>...
    """
    for index_name in args['<index_names>']:
        specific_index = IndexStrategy.get_specific_index(index_name)
        specific_index.pls_delete()


@search.subcommand('Create indicies and apply mappings')
def setup(args, argv):
    """
    Usage: {0} search setup <index_or_strategy_name>
           {0} search setup --initial
    """
    is_initial = args.get('--initial')
    if is_initial:
        specific_indexes = [
            index_strategy.for_current_index()
            for index_strategy in IndexStrategy.all_strategies()
        ]
    else:
        index_or_strategy_name = args['<index_or_strategy_name>']
        try:
            specific_indexes = [
                IndexStrategy.get_by_name(index_or_strategy_name).for_current_index(),
            ]
        except IndexStrategyError:
            try:
                specific_indexes = [
                    IndexStrategy.get_specific_index(index_or_strategy_name),
                ]
            except IndexStrategyError:
                raise IndexStrategyError(f'unrecognized index or strategy name "{index_or_strategy_name}"')
    for specific_index in specific_indexes:
        specific_index.pls_create()
        specific_index.pls_start_keeping_live()


@search.subcommand('Start the search indexing daemon')
def daemon(args, argv):
    """
    Usage: {0} search daemon
    """
    stop_event = IndexerDaemon.start_daemonthreads(celery_app)
    try:
        stop_event.wait()
    except KeyboardInterrupt:
        pass  # let the finally block stop all threads
    finally:
        if not stop_event.is_set():
            stop_event.set()
