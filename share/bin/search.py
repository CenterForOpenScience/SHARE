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
    _is_initial = args.get('--initial')
    if _is_initial:
        _specific_indexes = [
            _index_strategy.for_current_index()
            for _index_strategy in IndexStrategy.all_strategies()
        ]
    else:
        _index_or_strategy_name = args['<index_or_strategy_name>']
        try:
            _specific_indexes = [
                IndexStrategy.get_by_name(_index_or_strategy_name).for_current_index(),
            ]
        except IndexStrategyError:
            try:
                _specific_indexes = [
                    IndexStrategy.get_specific_index(_index_or_strategy_name),
                ]
            except IndexStrategyError:
                raise IndexStrategyError(f'unrecognized index or strategy name "{_index_or_strategy_name}"')
    for _specific_index in _specific_indexes:
        _index_strategy = _specific_index.index_strategy
        _preexisting_index_count = sum(
            _index.pls_check_exists()
            for _index in _index_strategy.each_specific_index()
        )
        _specific_index.pls_create()
        _specific_index.pls_start_keeping_live()
        if _is_initial:  # there's nothing back to fill; consider backfill already complete
            _backfill = _index_strategy.get_or_create_backfill()
            _backfill.backfill_status = _backfill.COMPLETE
            _backfill.save()
        if not _preexisting_index_count:  # first index for a strategy is automatic default
            _index_strategy.pls_make_default_for_searching(_specific_index)


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
