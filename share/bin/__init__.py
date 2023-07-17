import os
import sys

import django

from share.bin.util import execute_cmd


MODULES = (
    'harvest',
    'search',
)


def main(argv):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')  # noqa
    django.setup()

    for name in MODULES:
        __import__('share.bin.{}'.format(name))

    execute_cmd(argv[1:])


if __name__ == '__main__':
    main(sys.argv)
