import os

from django.apps import apps
from django.db.migrations.state import ProjectState
from django.core.management.base import BaseCommand
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.writer import MigrationWriter
from django.db.migrations.autodetector import MigrationAutodetector

from share.robot import RobotAppConfig
from share.robot import RobotMigration


class Command(BaseCommand):
    can_import_settings = True

    def add_arguments(self, parser):
        parser.add_argument('providers', nargs='*', type=str, help='App label(s) of the provider(s) to make migration(s) for')

    def write_migration(self, migration):
        loader = MigrationLoader(None, ignore_no_migrations=True)
        autodetector = MigrationAutodetector(loader.project_state(), ProjectState.from_apps(apps),)
        changes = autodetector.arrange_for_graph(changes={'share': [migration]}, graph=loader.graph,)

        for m in changes['share']:
            writer = MigrationWriter(m)
            with open(writer.path, 'wb') as fp:
                fp.write(writer.as_string())

    def handle(self, *args, **options):
        changes = {}
        if options.get('providers'):
            configs = [apps.get_app_config(label) for label in options['providers']]
        else:
            configs = apps.get_app_configs()

        for config in configs:
            if isinstance(config, RobotAppConfig):
                changes[config.name] = [RobotMigration(config).migration()]

        for migrations in changes.values():
            for m in migrations:
                writer = MigrationWriter(m)
                os.makedirs(os.path.dirname(writer.path), exist_ok=True)

                with open(os.path.join(os.path.dirname(writer.path), '__init__.py'), 'wb') as fp:
                    fp.write(b'')

                with open(writer.path, 'wb') as fp:
                    fp.write(writer.as_string())
