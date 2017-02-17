import datetime
import pendulum

from django.utils import timezone
from django.conf import settings
from django.core.management.base import BaseCommand

from share.tasks import HarvesterTask
from share.models import ShareUser, SourceConfig


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('source_config', type=str, help='The source config to be harvested')
        parser.add_argument('--async', action='store_true', help='Days')
        parser.add_argument('--interval', default=1, type=int, help='Days')
        parser.add_argument('--earliest', default=None, type=pendulum.parse, help='')
        parser.add_argument('--ignore-disabled', action='store_true', help='')
        parser.add_argument('--no-ingest', action='store_false', help='')

    def handle(self, *args, **options):
        source_config = SourceConfig.objects.get(label=options['source_config'])
        system_user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)

        now = timezone.now().date()
        end = (options.get('earliest') or source_config.earliest_date).date()

        while end < now:
            start, end = end, end + datetime.timedelta(options['interval'])

            if end > now:
                end = now

            if options['async']:
                HarvesterTask().apply_async((system_user.id, options['source_config'], ), {
                    'start': start.isoformat(),
                    'end': end.isoformat(),
                    'ingest': bool(options['no_ingest']),
                    'ignore_disabled': bool(options['ignore_disabled']),
                }, queue='backharvest', routing_key='backharvest')
                self.stdout.write('Started HarvesterTask({}, {}, {})'.format(options['source_config'], start, end))
            else:
                HarvesterTask().apply((system_user.id, options['source_config'], ), {
                    'start': start.isoformat(),
                    'end': end.isoformat(),
                    'ingest': bool(options['no_ingest']),
                    'ignore_disabled': bool(options['ignore_disabled'])
                }, throw=True)
