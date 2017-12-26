from django.contrib.staticfiles.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    # Override default port for `runserver` command
    default_port = "38000"
