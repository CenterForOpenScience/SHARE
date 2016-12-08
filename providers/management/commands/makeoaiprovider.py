import os

from cookiecutter.main import cookiecutter
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '[TLD] [short_title]'

    def add_arguments(self, parser):
        parser.add_argument('domain', type=str)
        parser.add_argument('title', type=str)

    def handle(self, *args, **options):
        owd = os.getcwd()

        domain = options['domain']
        title = options['title']

        if os.path.exists('providers/{}/{}'.format(domain, title)):
            self.emphasize('This provider already exists')
            return

        self.instruct('Add provider.{}.{} to INSTALLED_APPS in settings [Enter]'.format(domain, title))

        os.chdir('providers')
        if not os.path.isdir(domain):
            os.mkdir(domain)
            self.instruct('Add /{}.*/ to gitignore [Enter]'.format(domain))

        os.chdir(domain)

        cookiecutter('../management/ProviderCookieCutter', extra_context={'domain': domain, 'title': title})
        self.instruct('Add approved_sets to apps.py [Enter]')

        os.chdir(owd)

        self.stdout.write('Making migration...')
        if os.system('python manage.py makeprovidermigrations {}.{}'.format(domain, title)):
            self.emphasize('Migration failed.\nManually run ./manage.py makeprovidermigrations {}.{}'
                           .format(domain, title))

        self.stdout.write('Performing harvest...')
        success = not os.system('./bin/share harvest {}.{} -l 15'.format(domain, title))
        if success:
            self.instruct('Add an example record to __init__  [Enter]')
        if not success:
            self.emphasize('Harvest failure. Ideas:\nReview apps.py,\nTry time_granularity in apps.py,'
                           '\nHarvest further back than 15 days,\nFinally, try harvesting  again.')

        self.emphasize('Verify the favicon in static')
        self.stdout.write('Flake8...')
        os.system('flake8 providers/{}/{}'.format(domain, title))

    def emphasize(self, msg):
        self.stdout.write('\033[1;31mNotice: {}\033[0;0m'.format(msg))

    def instruct(self, msg):
        input('\033[1;36mUser task: {}\033[0;0m'.format(msg))
