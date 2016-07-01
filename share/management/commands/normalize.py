from django.core.management.base import BaseCommand
from django.conf import settings

from share.models import ShareUser
from share.tasks import NormalizerTask


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('normalizer', type=str, help='The name of the normalizer to run')
        parser.add_argument('raw_id', type=int, help='The id of the raw record to normalize')
        parser.add_argument('--async', action='store_true', help='Whether or not to use Celery')

    def handle(self, *args, **options):
        user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)

        if options['async']:
            NormalizerTask().apply_async((options['normalizer'], user.id, options['raw_id']))
        else:
            NormalizerTask().run(options['normalizer'], user.id, options['raw_id'])
