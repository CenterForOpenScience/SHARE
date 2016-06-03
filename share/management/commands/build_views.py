from django.apps import apps
from django.core.management.base import BaseCommand
from django.db.migrations import Migration
from django.db.migrations import operations
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState
from django.db.migrations.writer import MigrationWriter

from share.models.base import ShareAbstract


class Command(BaseCommand):

    MATERIALIZED_VIEW = '''
        CREATE MATERIALIZED VIEW {concrete} AS (
            SELECT version.*
            FROM {current} AS current
            LEFT JOIN {version} AS version
            ON current.version = version.id
        ) WITH DATA;
    '''

    MATERIALIZED_VIEW_REVERSE = '''
        DROP MATERIALIZED VIEW {concrete};
    '''

    PROCEDURE = '''
        CREATE OR REPLACE FUNCTION after_{version}_insert() RETURNS trigger AS $$
        BEGIN
            INSERT INTO {current}(id, version)
            VALUES(NEW.p_id, NEW.id)
            ON CONFLICT (id) DO UPDATE
            SET version=NEW.id;
        RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    '''

    PROCEDURE_REVERSE = '''
        DROP FUNCTION after_{version}_insert();
    '''

    TRIGGER = '''
        CREATE TRIGGER {version}_insert
        AFTER INSERT ON {version}
        FOR EACH ROW
        EXECUTE PROCEDURE after_{version}_insert();
    '''

    TRIGGER_REVERSE = '''
        DROP TRIGGER {version}_insert
    '''

    can_import_settings = True

    def handle(self, *args, **options):
        ops = []

        for model in apps.get_models(include_auto_created=True):
            if not issubclass(model, ShareAbstract):
                continue

            names = {
                'concrete': model._meta.db_table,
                'version': model.Version._meta.db_table,
                'current': model.Current._meta.db_table,
            }

            ops.extend([
                operations.RunSQL(self.MATERIALIZED_VIEW.format(**names).strip(), reverse_sql=self.MATERIALIZED_VIEW_REVERSE.format(**names).strip()),
                operations.RunSQL(self.PROCEDURE.format(**names).strip(), reverse_sql=self.PROCEDURE_REVERSE.format(**names).strip()),
                operations.RunSQL(self.TRIGGER.format(**names).strip(), reverse_sql=self.TRIGGER_REVERSE.format(**names).strip()),
            ])

        m = Migration('create_triggers_views', 'share')
        m.operations = ops

        loader = MigrationLoader(None, ignore_no_migrations=True)
        autodetector = MigrationAutodetector(loader.project_state(), ProjectState.from_apps(apps),)
        changes = autodetector.arrange_for_graph(changes={'share': [m]}, graph=loader.graph,)

        for migration in changes['share']:
            writer = MigrationWriter(migration)
            with open(writer.path, 'wb') as fp:
                fp.write(writer.as_string())
