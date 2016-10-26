from django.apps import apps
from django.core.management.base import BaseCommand
from django.conf import settings

from share.models import ShareUser, NormalizedData
from share.tasks import MakeJsonPatches


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('source', type=str, help='The name of the provider to run')
        parser.add_argument('normalized', nargs='*', type=int, help='The id(*) of the normalized data to make changes for')
        parser.add_argument('--all', action='store_true', help='Make changes for all normalized data for the source specified')
        parser.add_argument('--async', action='store_true', help='Whether or not to use Celery')

    def handle(self, *args, **options):
        user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)
        config = apps.get_app_config(options['source'])

        if not options['normalized'] and options['all']:
            options['normalized'] = NormalizedData.objects.filter(raw__app_label=config.label).values_list('id', flat=True)

        for id in options['normalized']:
            task_args = (id, user.id)

            if options['async']:
                MakeJsonPatches().apply_async(task_args)
            else:
                MakeJsonPatches().apply(task_args, throw=True)
