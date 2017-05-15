import json

from django.conf import settings
from django.core.management.base import BaseCommand

from share.tasks import BotTask
from share.models import ShareUser

from bots.elasticsearch.tasks import JanitorTask


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--last-run', type=int, help='The timestmap of the last run')
        parser.add_argument('--async', action='store_true', help='Whether or not to use Celery')
        parser.add_argument('--url', type=str, help='Force the value of ELASTICSEARCH_URL for all tasks and subtasks')
        parser.add_argument('--index', type=str, help='Force the value of ELASTICSEARCH_INDEX for all tasks and subtasks')
        parser.add_argument('--setup', action='store_true', help='Set up Elasticsearch index, settings, and mappings')
        parser.add_argument('--filter', type=json.loads, help='Set up Elasticsearch index, including settings and mappings')
        parser.add_argument('--models', nargs='*', type=str, help='Only index the given models')
        parser.add_argument('--janitor', action='store_true', help='Run the janitor task')
        parser.add_argument('--dry', action='store_true', help='When running with --janitor, don\'t reindex missing documents')

    def handle(self, *args, **options):
        user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)
        task_args = (user.id, 'elasticsearch', )
        task_kwargs = {k: v for k, v in {
            'last_run': options['last_run'],
            'es_url': options.get('url'),
            'es_index': options.get('index'),
            'es_setup': options.get('setup'),
            'es_filter': options.get('filter'),
            'es_models': options.get('models'),
        }.items() if v}

        if options['janitor']:
            task_kwargs['dry'] = bool(options.get('dry', False))
            if options['async']:
                JanitorTask().apply_async(task_args, task_kwargs)
            else:
                JanitorTask().apply(task_args, task_kwargs)
            return 0

        if options['async']:
            BotTask().apply_async(task_args, task_kwargs)
            self.stdout.write('Started job for elasticsearch')
        else:
            self.stdout.write('Running elasticsearch')
            BotTask().apply(task_args, task_kwargs, throw=True)
