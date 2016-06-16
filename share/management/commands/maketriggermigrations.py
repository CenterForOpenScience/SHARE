import os

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db.migrations import Migration
from django.db.migrations import operations
from django.db.migrations.writer import MigrationWriter

from share.models.base import ShareObject


# Triggers are Faster and will run in any insert/update situation
# Model based logic will not run in certain scenarios. IE Bulk operations
class Command(BaseCommand):
    can_import_settings = True

    PROCEDURE = '''
        CREATE OR REPLACE FUNCTION before_{concrete}_change() RETURNS trigger AS $$
        DECLARE
            vid INTEGER;
        BEGIN
            INSERT INTO {version}({columns}) VALUES ({new_columns}) RETURNING (id) INTO vid;
            NEW.version_id = vid;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    '''

    PROCEDURE_REVERSE = '''
        DROP FUNCTION before_{concrete}_change();
    '''

    TRIGGER = '''
        DROP TRIGGER IF EXISTS {concrete}_change ON {concrete};

        CREATE TRIGGER {concrete}_change
        BEFORE INSERT OR UPDATE ON {concrete}
        FOR EACH ROW
        EXECUTE PROCEDURE before_{concrete}_change();
    '''

    TRIGGER_REVERSE = '''
        DROP TRIGGER {concrete}_change
    '''

    def collect_fields(self, model):
        concrete_fields = ['NEW.' + f.column for f in model._meta.fields]
        version_fields = [f.column for f in model.VersionModel._meta.fields]

        version_fields.remove('id')
        version_fields.remove('action')
        version_fields.remove('persistant_id')
        concrete_fields.remove('NEW.id')
        concrete_fields.remove('NEW.version_id')

        assert len(version_fields) == len(concrete_fields)

        return concrete_fields, version_fields

    def build_operations(self, model):
        concrete_fields, version_fields = self.collect_fields(model)

        params = {
            'concrete': model._meta.db_table,
            'version': model.VersionModel._meta.db_table,
            'columns': ', '.join(['persistant_id', 'action'] + sorted(version_fields)),
            'new_columns': ', '.join(['NEW.id', 'TG_OP'] + sorted(concrete_fields)),
        }

        return [
            operations.RunSQL(self.PROCEDURE.format(**params).strip(), reverse_sql=self.PROCEDURE_REVERSE.format(**params).strip()),
            operations.RunSQL(self.TRIGGER.format(**params).strip(), reverse_sql=self.TRIGGER_REVERSE.format(**params).strip()),
        ]

    def write_migration(self, migration):
        writer = MigrationWriter(migration)
        os.makedirs(os.path.dirname(writer.path), exist_ok=True)
        with open(writer.path, 'wb') as fp:
            fp.write(writer.as_string())

    def handle(self, *args, **options):
        ops = []

        for model in apps.get_models(include_auto_created=True):
            if not issubclass(model, ShareObject):
                continue
            ops.extend(self.build_operations(model))

        m = Migration('0002_triggers', 'share')
        m.operations = ops
        m.dependencies = [('share', '0001_initial')]

        self.write_migration(m)
