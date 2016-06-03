from django.apps import apps
from django.core.management.base import BaseCommand
from django.db.migrations import Migration
from django.db.migrations import operations
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState
from django.db.migrations.writer import MigrationWriter

from share.models.base import ShareConcrete

# Triggers are Faster and will run in any insert/update situation
# Model based logic will not run in certain scenarios. IE Bulk operations
class Command(BaseCommand):

    PROCEDURE = '''
        CREATE OR REPLACE FUNCTION after_{concrete}_change() RETURNS trigger AS $$
        DECLARE
            vid INTEGER;
        BEGIN
            INSERT INTO {version}({columns}) VALUES({new_columns}) RETURNING (id) INTO vid;
            INSERT INTO {pointer}(id, version_id) VALUES(NEW.id, vid) ON CONFLICT(id) DO UPDATE SET version_id=vid;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    '''

    PROCEDURE_REVERSE = '''
        DROP FUNCTION after_{concrete}_change();
    '''

    CREATE_TRIGGER = '''
        CREATE TRIGGER {concrete}_insert
        AFTER INSERT ON {concrete}
        FOR EACH ROW
        EXECUTE PROCEDURE after_{concrete}_change();
    '''

    CREATE_TRIGGER_REVERSE = '''
        DROP TRIGGER {concrete}_insert
    '''

    UPDATE_TRIGGER = '''
        CREATE TRIGGER {concrete}_update
        AFTER UPDATE ON {concrete}
        FOR EACH ROW
        EXECUTE PROCEDURE after_{concrete}_change();
    '''

    UPDATE_TRIGGER_REVERSE = '''
        DROP TRIGGER {concrete}_update
    '''

    can_import_settings = True

    def handle(self, *args, **options):
        ops = []

        for model in apps.get_models(include_auto_created=True):
            if not issubclass(model, ShareConcrete):
                continue

            concrete_fields = ['NEW.' + f.column for f in model._meta.fields]
            version_fields = [f.column for f in model.Version._meta.fields]

            version_fields.remove('id')
            version_fields.remove('persistant_id')
            concrete_fields.remove('NEW.id')

            assert len(version_fields) == len(concrete_fields)

            params = {
                'concrete': model._meta.db_table,
                'version': model.Version._meta.db_table,
                'pointer': model.Current._meta.db_table,
                'columns': ', '.join(['persistant_id'] + sorted(version_fields)),
                'new_columns': ', '.join(['NEW.id'] + sorted(concrete_fields)),
            }

            ops.extend([
                operations.RunSQL(self.PROCEDURE.format(**params).strip(), reverse_sql=self.PROCEDURE_REVERSE.format(**params).strip()),
                operations.RunSQL(self.CREATE_TRIGGER.format(**params).strip(), reverse_sql=self.CREATE_TRIGGER_REVERSE.format(**params).strip()),
                operations.RunSQL(self.UPDATE_TRIGGER.format(**params).strip(), reverse_sql=self.UPDATE_TRIGGER_REVERSE.format(**params).strip()),
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
