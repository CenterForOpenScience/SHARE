from django.apps import apps
from django.core.management.base import BaseCommand
from django.conf import settings

from share.models import ShareUser, RawData
from share.tasks import NormalizerTask


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('normalizer', type=str, help='The name of the provider to run')
        parser.add_argument('raws', nargs='*', type=int, help='The id(s) of the raw record to normalize')
        parser.add_argument('--all', action='store_true', help='Normalize all data for the provider specified')
        parser.add_argument('--async', action='store_true', help='Whether or not to use Celery')

    def handle(self, *args, **options):
        user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)
        config = apps.get_app_config(options['normalizer'])

        if not options['raws'] and options['all']:
            options['raws'] = RawData.objects.filter(app_label=config.label).values_list('id', flat=True)

        for raw in options['raws']:
            task_args = (config.label, user.id, raw,)

            if options['async']:
                NormalizerTask().apply_async(task_args)
            else:
                NormalizerTask().apply(task_args, throw=True)
