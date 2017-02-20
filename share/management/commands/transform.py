from django.core.management.base import BaseCommand
from django.conf import settings

from share.models import ShareUser, RawData, SourceConfig
from share.tasks import NormalizerTask


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('source-config', type=str, help='The name of the SourceConfig to use')
        parser.add_argument('raws', nargs='*', type=int, help='The id(s) of the raw record to transform')
        parser.add_argument('--all', action='store_true', help='Normalize all data for the provider specified')
        parser.add_argument('--async', action='store_true', help='Whether or not to use Celery')

    def handle(self, *args, **options):
        user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)
        config = SourceConfig.objects.get(label=options['source-config'])

        if not options['raws'] and options['all']:
            options['raws'] = RawData.objects.filter(suid__source_config_id=config.id).values_list('id', flat=True)

        for raw in options['raws']:
            task_args = (user.id, config.label, raw,)

            if options['async']:
                NormalizerTask().apply_async(task_args)
            else:
                NormalizerTask().apply(task_args, throw=True)
