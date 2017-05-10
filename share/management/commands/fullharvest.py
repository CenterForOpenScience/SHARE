import datetime
import pendulum

from django.utils import timezone
from django.db import transaction
from django.core.management.base import BaseCommand

from share.tasks import HarvesterTask
from share.models import SourceConfig, HarvestLog


def parse_date(date):
    return pendulum.parse(date).date()


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('source_config', type=str, help='The source config to be harvested')
        parser.add_argument('--async', action='store_true', help='Days')
        parser.add_argument('--interval', default=1, type=int, help='Days')
        parser.add_argument('--start', default=None, type=parse_date, help='')
        parser.add_argument('--end', default=None, type=parse_date, help='')
        parser.add_argument('--ignore-disabled', action='store_true', help='')
        parser.add_argument('--no-ingest', action='store_false', help='')
        parser.add_argument('--superfluous', action='store_true', help='')
        parser.add_argument('--quiet', action='store_true', help='')

    def handle(self, *args, **options):
        source_config = SourceConfig.objects.filter(label=options['source_config'])[0]

        start = options.get('start') or source_config.earliest_date
        end = options.get('end') or timezone.now().date()
        start, end = HarvesterTask.resolve_date_range(start, end)
        quiet = options.pop('quiet')

        fields = ('start_date', 'end_date', 'source_config', 'harvester_version', 'source_config_version')
        data = (
            (*dates, source_config.id, source_config.harvester.version, source_config.version)
            for dates in self._date_gen(start, end, datetime.timedelta(options.pop('interval')))
        )

        with transaction.atomic():
            for log in HarvestLog.objects.bulk_create_or_get(fields, data):
                log._source_config_cache = source_config
                log.spawn_task(**{
                    k: v for k, v in options.items()
                    if k in ('limit', 'force', 'superfluous', 'ingest', 'ignore_disabled')
                })
                if not quiet:
                    self.stdout.write('Started HarvesterTask({}, {}, {})'.format(options['source_config'], log.start_date, log.end_date))

    def _date_gen(self, start, end, interval):
        task_end = start
        while task_end < end:
            task_start, task_end = task_end, task_end + interval

            if task_end > end:
                task_end = end

            yield task_start, task_end
