from django.core.management.base import BaseCommand

from share.tasks import run_harvester


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('harvester', type=str, help='The name of the harvester to run')
        parser.add_argument('--async', action='store_true', help='Whether or not to use Celery')

    def handle(self, *args, **options):
        if options['async']:
            run_harvester.apply_async((options['harvester'],))
        else:
            run_harvester(options['harvester'])
