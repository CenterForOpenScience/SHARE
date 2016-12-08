import os
import logging

from cookiecutter.main import cookiecutter
from django.core.management.base import BaseCommand

logger = logging.getLogger('name')


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
            logger.error('This provider already exists')
            return

        input('Add provider.{}.{} to INSTALLED_APPS in settings: [Enter]'.format(domain, title))

        os.chdir('providers')
        if not os.path.isdir(domain):
            os.mkdir(domain)
            input('Add /{}.*/ to gitignore: [Enter]'.format(domain))

        os.chdir(domain)

        cookiecutter('../management/ProviderCookieCutter', extra_context={'domain': domain, 'title': title})
        input('Add approved_sets to apps.py: [Enter]')

        os.chdir(owd)

        self.stdout.write('Making migration...')
        if os.system('python manage.py makeprovidermigrations {}.{}'.format(domain, title)):
            logger.error('Migration failed. '
                         'Manually run ./manage.py makeprovidermigrations {}.{}'.format(domain, title))

        self.stdout.write('Performing harvest...')
        success = not os.system('./bin/share harvest {}.{} -l 15'.format(domain, title))
        if success:
            input('Add an example record to __init__:  [Enter]')
        if not success:
            logger.error('Harvest failure. Ideas:'
                              'Review apps.py,'
                              'Try time_granularity in apps.py, '
                              'Harvest further back than 15 days,'
                              'Finally, try harvesting  again.')

        logger.warning('Verify the favicon in static')
        self.stdout.write('Flake8...')
        os.system('flake8 providers/{}/{}'.format(domain, title))
