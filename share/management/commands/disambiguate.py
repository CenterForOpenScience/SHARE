from django.apps import apps
from django.core.management.base import BaseCommand
from django.conf import settings

from share.models import NormalizedData
from share.tasks import disambiguate


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('normalized', nargs='*', type=int, help='The id(*) of the normalized data to make changes for')
        parser.add_argument('--source', type=str, help='Name of a Source, to disambiguate ALL its normalized data')
        parser.add_argument('--async', action='store_true', help='Whether or not to use Celery')

    def handle(self, *args, **options):
        ids = options['normalized']
        if options['source']:
            ids.extend(NormalizedData.objects.filter(source__source__name=options['source']).values_list('id', flat=True))
        for id in ids:
            if options['async']:
                disambiguate.apply_async((id,))
            else:
                disambiguate(id)
