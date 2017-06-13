import os
import sys

import django

from share.bin.util import execute_cmd


MODULES = (
    'debug',
    'harvest',
    'info',
    'ingest',
    'services',
    'elastic',
)


def main(argv):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')  # noqa
    django.setup()

    for name in MODULES:
        __import__('share.bin.{}'.format(name))

    execute_cmd(sys.argv[1:])

if __name__ == '__main__':
    main(sys.argv)
