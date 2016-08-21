import arrow
import datetime

from django.apps import apps
from django.core.management.base import BaseCommand
from django.conf import settings

from share.models import ShareUser
from share.tasks import HarvesterTask
from share.provider import ProviderAppConfig


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Run all harvesters')
        parser.add_argument('harvester', nargs='*', type=str, help='The name of the harvester to run')
        parser.add_argument('--async', action='store_true', help='Whether or not to use Celery')

        parser.add_argument('--days-back', type=int, help='The number of days to go back, defaults to 1')
        parser.add_argument('--start', type=str, help='The day to start harvesting, in the format YYYY-MM-DD')
        parser.add_argument('--end', type=str, help='The day to end harvesting, in the format YYYY-MM-DD')

    def handle(self, *args, **options):
        user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)

        task_kwargs = {}

        if options['days_back'] and (options['start'] or options['end']):
            self.stdout.write('Please choose days-back OR a start date with end date, not both')
            return

        if options['days_back']:
            task_kwargs['end'] = datetime.datetime.utcnow() + datetime.timedelta(days=-(options['days_back'] - 1))
            task_kwargs['start'] = datetime.datetime.utcnow() + datetime.timedelta(days=-options['days_back'])
        else:
            task_kwargs['start'] = arrow.get(options['start']) if options.get('start') else arrow.utcnow() - datetime.timedelta(days=int(options['days_back'] or 1))
            task_kwargs['end'] = arrow.get(options['end']) if options.get('end') else arrow.utcnow()

        task_kwargs['end'] = task_kwargs['end'].isoformat() + 'Z'
        task_kwargs['start'] = task_kwargs['start'].isoformat() + 'Z'

        if not options['harvester'] and options['all']:
            options['harvester'] = [x.label for x in apps.get_app_configs() if isinstance(x, ProviderAppConfig) and not x.disabled]

        for harvester in options['harvester']:
            apps.get_app_config(harvester)  # Die if the AppConfig can not be loaded

            task_args = (harvester, user.id,)
            if options['async']:
                HarvesterTask().apply_async(task_args, task_kwargs)
                self.stdout.write('Started job for harvester {}'.format(harvester))
            else:
                self.stdout.write('Running harvester for {}'.format(harvester))
                HarvesterTask().apply(task_args, task_kwargs, throw=True)
