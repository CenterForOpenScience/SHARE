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
        parser.add_argument('--async', action='store_true', help='Whether or not to use Celery')

    def handle(self, *args, **options):
        user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)

        if not options['bot'] and options['all']:
            options['bot'] = [x.label for x in apps.get_app_configs() if isinstance(x, BotAppConfig)]

        for bot in options['bot']:
            apps.get_app_config(bot)  # Die if the AppConfig can not be loaded

            task_args = (bot, user.id,)

            if options['async']:
                BotTask().apply_async(task_args)
                self.stdout.write('Started job for bot {}'.format(bot))
            else:
                self.stdout.write('Running bot for {}'.format(bot))
                BotTask().apply(task_args, throw=True)
