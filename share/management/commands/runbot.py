from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand

from share.tasks import BotTask
from share.models import ShareUser
from share.bot import BotAppConfig


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Run all harvester')
        parser.add_argument('bot', nargs='*', type=str, help='The name of the bot to run')
        parser.add_argument('--last-run', type=int, help='The timestmap of the last run')
        parser.add_argument('--async', action='store_true', help='Whether or not to use Celery')
        parser.add_argument('--es-url', type=str, help='Force the value of ELASTICSEARCH_URL for all tasks and subtasks')
        parser.add_argument('--es-index', type=str, help='Force the value of ELASTICSEARCH_INDEX for all tasks and subtasks')
        parser.add_argument('--es-setup', action='store_true', help='Set up Elasticsearch index, including settings and mappings')

    def handle(self, *args, **options):
        user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)

        if not options['bot'] and options['all']:
            options['bot'] = [x.label for x in apps.get_app_configs() if isinstance(x, BotAppConfig)]

        for bot in options['bot']:
            apps.get_app_config(bot)  # Die if the AppConfig can not be loaded

            task_args = (user.id, bot, )
            task_kwargs = {'last_run': options['last_run']}

            if bot == 'elasticsearch':
                task_kwargs['es_url'] = options.get('es_url')
                task_kwargs['es_index'] = options.get('es_index')
                task_kwargs['es_setup'] = options.get('es_setup')

            if options['async']:
                BotTask().apply_async(task_args, task_kwargs)
                self.stdout.write('Started job for bot {}'.format(bot))
            else:
                self.stdout.write('Running bot for {}'.format(bot))
                BotTask().apply(task_args, task_kwargs, throw=True)
