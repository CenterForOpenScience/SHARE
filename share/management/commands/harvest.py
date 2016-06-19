import datetime

from django.core.management.base import BaseCommand

from share.tasks import run_harvester


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('harvester', type=str, help='The name of the harvester to run')
        parser.add_argument('--async', action='store_true', help='Whether or not to use Celery')
        parser.add_argument('--days-back', type=int, help='The number of days to go back')

    def handle(self, *args, **options):
        kwargs = {}
        if options['days_back']:
            kwargs['end'] = datetime.datetime.utcnow() + datetime.timedelta(days=-(options['days_back'] - 1))
            kwargs['start'] = datetime.datetime.utcnow() + datetime.timedelta(days=-options['days_back'])

        if options['async']:
            run_harvester.apply_async((options['harvester'],), **kwargs)
        else:
            run_harvester(options['harvester'], **kwargs)
