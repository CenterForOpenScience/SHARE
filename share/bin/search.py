import threading

from project.celery import app as celery_app

from django.db.models import Exists, OuterRef

from share.bin.util import command
from share.models import FormattedMetadataRecord, SourceUniqueIdentifier
from share.search import MessageType, SearchHelper, IndexSetup
from share.search.daemon import IndexMessengerDaemon


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
        index_setup = IndexSetup.by_name(index_name)
        index_setup.pls_delete()


@search.subcommand('Create indicies and apply mappings')
def setup(args, argv):
    """
    Usage: {0} search setup <index_name>
           {0} search setup --initial
    """
    is_initial = args.get('--initial')
    if is_initial:
        index_setups = IndexSetup.all_indexes()
    else:
        index_setups = [IndexSetup.by_name(args['<index_name>'])]
    for index_setup in index_setups:
        index_setup.pls_setup_as_needed()


@search.subcommand('Queue daemon messages to reindex all suids')
def reindex_all_suids(args, argv):
    """
    Usage: {0} search reindex_all_suids <index_name>

    Most likely useful for a freshly `setup` index (perhaps after a purge).
    """
    # TODO check for a specific format of FMR, not just that *any* FMR exists
    suid_id_queryset = (
        SourceUniqueIdentifier.objects
        .annotate(
            has_fmr=Exists(
                FormattedMetadataRecord.objects.filter(suid_id=OuterRef('id'))
            )
        )
        .filter(has_fmr=True)
        .values_list('id', flat=True)
    )
    SearchHelper().send_messages(
        message_type=MessageType.INDEX_SUID,
        target_ids_chunk=suid_id_queryset,
        index_names=[args['<index_name>']],
    )


@search.subcommand('Start the search indexing daemon')
def daemon(args, argv):
    """
    Usage: {0} search daemon
    """
    stop_event = threading.Event()
    IndexMessengerDaemon.start_daemonthreads(celery_app, stop_event)
    try:
        stop_event.wait()
    except KeyboardInterrupt:
        pass  # let the finally block stop all threads
    finally:
        if not stop_event.is_set():
            stop_event.set()
