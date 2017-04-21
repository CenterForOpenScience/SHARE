#!/usr/bin/env python
import os
import sys

import django

if os.environ.get('GEVENT') == '1':
    from gevent import monkey
    monkey.patch_all()

    from psycogreen.gevent import patch_psycopg
    patch_psycopg()

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

    # Override default port for `runserver` command
    django.setup()
    from django.core.management.commands.runserver import Command as runserver
    runserver.default_port = "38000"

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
