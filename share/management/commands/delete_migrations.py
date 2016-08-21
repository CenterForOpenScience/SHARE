from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import subprocess


class Command(BaseCommand):
    help = 'Deletes migrations'

    def handle(self, *args, **options):
        cmd = [
            'find',
            settings.BASE_DIR,
            '-path', '*migrations/*',
            '-name', '"[0-9][0-9][0-9][0-9]_*.py"',
            '-not', '-path', '"*__init__*"',
            '-delete'
        ]
        output = subprocess.getoutput(' '.join(cmd))
        self.stdout.write(self.style.SUCCESS('Deleted all migrations'))