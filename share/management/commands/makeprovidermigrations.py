import os

from django.apps import apps
from django.db.migrations.state import ProjectState
from django.core.management.base import BaseCommand
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.writer import MigrationWriter
from django.db.migrations.autodetector import MigrationAutodetector

from share.core import ProviderAppConfig
from share.core import ProviderMigration


class Command(BaseCommand):
    can_import_settings = True

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
        for config in apps.get_app_configs():
            if isinstance(config, ProviderAppConfig):
                changes[config.name] = [ProviderMigration(config).migration()]

        for migrations in changes.values():
            for m in migrations:
                writer = MigrationWriter(m)
                os.makedirs(os.path.dirname(writer.path), exist_ok=True)

                with open(os.path.join(os.path.dirname(writer.path), '__init__.py'), 'wb') as fp:
                    fp.write(writer.as_string())

                with open(writer.path, 'wb') as fp:
                    fp.write(writer.as_string())
