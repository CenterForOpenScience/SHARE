import threading

from project.celery import app as celery_app

from share.bin.util import command
from share.search import IndexStrategy
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
        index_strategy = IndexStrategy.by_specific_index_name(index_name)
        index_strategy.pls_delete()


@search.subcommand('Create indicies and apply mappings')
def setup(args, argv):
    """
    Usage: {0} search setup <index_name>
           {0} search setup --initial
    """
    is_initial = args.get('--initial')
    if is_initial:
        index_strategys = IndexStrategy.all_strategies().values()
    else:
        index_strategys = [IndexStrategy.by_request(args['<index_name>'])]
    for index_strategy in index_strategys:
        index_strategy.pls_setup_as_needed()


@search.subcommand('Queue daemon messages to reindex all suids')
def reindex_all_suids(args, argv):
    """
    Usage: {0} search reindex_all_suids <index_name>

    Most likely useful for a freshly `setup` index (perhaps after a purge).
    """
    index_strategy = IndexStrategy.by_request(args['<index_name>'])
    index_strategy.pls_setup_as_needed(start_backfill=True)


@search.subcommand('Start the search indexing daemon')
def daemon(args, argv):
    """
    Usage: {0} search daemon
    """
    stop_event = threading.Event()
    IndexerDaemon.start_daemonthreads(celery_app, stop_event)
    try:
        stop_event.wait()
    except KeyboardInterrupt:
        pass  # let the finally block stop all threads
    finally:
        if not stop_event.is_set():
            stop_event.set()
