#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "share.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

# python manage.py makemigrations polls
# python manage.py sqlmigrate polls 0001
# python manage.py migrate
# python manage.py runserver
# python manage.py createsuperuser