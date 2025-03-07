from project.celery import app as celery_app

from share.bin.util import command
from share.search import index_strategy
from share.search.exceptions import IndexStrategyError
from share.search.daemon import IndexerDaemonControl


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
    Usage: {0} search purge <strategy_names>...
    """
    for _strategy_name in args['<strategy_names>']:
        _strategy = index_strategy.parse_strategy_name(_strategy_name)
        _strategy.pls_teardown()


@search.subcommand('Create indicies and apply mappings')
def setup(args, argv):
    """
    Usage: {0} search setup <index_or_strategy_name>
           {0} search setup --initial
    """
    _is_initial = args.get('--initial')
    if _is_initial:
        for _index_strategy in index_strategy.each_strategy():
            _index_strategy.pls_setup()
    else:
        _index_or_strategy_name = args['<index_or_strategy_name>']
        try:
            _strategy = index_strategy.get_strategy(_index_or_strategy_name)
        except IndexStrategyError:
            raise IndexStrategyError(f'unrecognized index or strategy name "{_index_or_strategy_name}"')
        else:
            _strategy.pls_setup()


@search.subcommand('Start the search indexing daemon')
def daemon(args, argv):
    """
    Usage: {0} search daemon
    """
    _daemon_control = IndexerDaemonControl(celery_app)
    _daemon_control.start_all_daemonthreads()
    try:
        _daemon_control.stop_event.wait()
    except KeyboardInterrupt:
        pass  # no error here; let the finally block stop all threads
    finally:
        _daemon_control.stop_daemonthreads(wait=True)
