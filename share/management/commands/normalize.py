from django.core.management.base import BaseCommand

from share.tasks import run_normalizer


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('normalizer', type=str, help='The name of the normalizer to run')
        parser.add_argument('--async', action='store_true', help='Whether or not to use Celery')

    def handle(self, *args, **options):
        if options['async']:
            run_normalizer.apply_async((options['normalizer'],))
        else:
            run_normalizer(options['normalizer'])
