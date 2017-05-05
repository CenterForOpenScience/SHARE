from share.bin.util import command


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
        -l, --loglevel=LOGLEVEL  Logging level. [Default: INFO]

    For local development only. Deployments should use the celery binary.
    """
    from project.celery import app

    worker = app.Worker(loglevel=args['--loglevel'], beat=args['--beat'])
    worker.start()
    return worker.exitcode
