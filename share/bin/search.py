import threading

from project.celery import app as celery_app

from django.conf import settings
from django.db.models import Exists, OuterRef

from share.bin.util import command
from share.models import FormattedMetadataRecord, SourceUniqueIdentifier
from share.search import MessageType, SearchIndexer
from share.search.daemon import SearchIndexerDaemon
from share.search.elastic_manager import ElasticManager


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
        ElasticManager().delete_index(index_name)


@search.subcommand('Create indicies and apply mappings')
def setup(args, argv):
    """
    Usage: {0} search setup <index_name>
           {0} search setup --initial
    """
    is_initial = args.get('--initial')

    if is_initial:
        index_names = settings.ELASTICSEARCH['ACTIVE_INDEXES']
    else:
        index_names = [args['<index_name>']]

    elastic_manager = ElasticManager()
    for index_name in index_names:
        print(f'creating elasticsearch index "{index_name}"...')
        elastic_manager.create_index(index_name)

    if is_initial:
        primary_index = index_names[0]
        elastic_manager.update_primary_alias(primary_index)


@search.subcommand('Update mappings for an existing index')
def update_mappings(args, argv):
    """
    Usage: {0} search update_mappings <index_name>
    """
    ElasticManager().update_mappings(args['<index_name>'])


@search.subcommand('Set the "primary" index used to serve search results')
def set_primary(args, argv):
    """
    Usage: {0} search set_primary <index_name>
    """
    ElasticManager().update_primary_alias(args['<index_name>'])


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
    SearchIndexer().send_messages(
        message_type=MessageType.INDEX_SUID,
        target_ids=suid_id_queryset,
        index_names=[args['<index_name>']],
    )


@search.subcommand('Start the search indexing daemon')
def daemon(args, argv):
    """
    Usage: {0} search daemon
    """
    elastic_manager = ElasticManager()
    stop_event = threading.Event()
    for index_name in settings.ELASTICSEARCH['ACTIVE_INDEXES']:
        SearchIndexerDaemon.start_indexer_in_thread(celery_app, stop_event, elastic_manager, index_name)

    try:
        stop_event.wait()
    except KeyboardInterrupt:
        pass  # let the finally block stop all threads
    finally:
        if not stop_event.is_set():
            stop_event.set()
