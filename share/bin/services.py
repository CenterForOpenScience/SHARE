import logging
import threading

from celery.signals import worker_ready
from celery.signals import worker_shutdown

from share.bin.util import command
from share.search.daemon import SearchIndexerDaemon


@command('Launch the SHARE API server', parsed=False)
def server(args, argv):
    from django.core.management import execute_from_command_line
    execute_from_command_line(['', 'runserver'] + argv[1:])


@command('Launch a Celery worker')
def worker(args, argv):
    """
    Usage: {0} worker [options]

    Options:
        -B, --beat                Also run the celery beat periodic task scheduler.
        -l, --loglevel=LOGLEVEL   Logging level. [Default: INFO]
        -I, --indexer             Also run the search indexer daemon.

    For local development only. Deployments should use the celery binary.
    """
    from project.celery import app

    if args['--indexer']:
        sid = SearchIndexerDaemon(app)

        @worker_ready.connect
        def start_sid(*args, **kwargs):
            threading.Thread(target=sid.run, daemon=True).start()

        @worker_shutdown.connect
        def stop_sid(*args, **kwargs):
            sid._running = False

    worker = app.Worker(loglevel=getattr(logging, args['--loglevel'].upper()), beat=args['--beat'])
    worker.start()
    return worker.exitcode
