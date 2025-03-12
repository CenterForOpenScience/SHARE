from django.core.management.base import BaseCommand
from share.search.daemon import IndexerDaemonControl
from project.celery import app as celery_app

class Command(BaseCommand):
    help = "Start the search indexing daemon"

    def handle(self, *args, **options):
        daemon_control = IndexerDaemonControl(celery_app)
        daemon_control.start_all_daemonthreads()
        try:
            daemon_control.stop_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            daemon_control.stop_daemonthreads(wait=True)
