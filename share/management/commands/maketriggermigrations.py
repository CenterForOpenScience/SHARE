import datetime
import os

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations import Migration
from django.db.migrations import operations
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.writer import MigrationWriter


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
        version_fields.remove('persistent_id')
        concrete_fields.remove('NEW.id')
        concrete_fields.remove('NEW.version_id')

        assert len(version_fields) == len(concrete_fields)

        return concrete_fields, version_fields

    def build_operations(self, model):
        concrete_fields, version_fields = self.collect_fields(model)

        params = {
            'concrete': model._meta.db_table,
            'version': model.VersionModel._meta.db_table,
            'columns': ', '.join(['persistent_id', 'action'] + sorted(version_fields)),
            'new_columns': ', '.join(['NEW.id', 'TG_OP'] + sorted(concrete_fields)),
        }

        return [
            operations.RunSQL(self.PROCEDURE.format(**params).strip(), reverse_sql=self.PROCEDURE_REVERSE.format(**params).strip()),
            operations.RunSQL(self.TRIGGER.format(**params).strip(), reverse_sql=self.TRIGGER_REVERSE.format(**params).strip()),
        ]

    def write_migration(self, migration):
        writer = MigrationWriter(migration)
        os.makedirs(os.path.dirname(writer.path), exist_ok=True)
        with open(writer.path, 'w') as fp:
            fp.write(writer.as_string())

    def handle(self, *args, **options):
        ops = []

        for model in apps.get_models(include_auto_created=True):
            if not hasattr(model, 'VersionModel') or model._meta.proxy:
                continue
            ops.extend(self.build_operations(model))
        if options['initial']:
            m = Migration('0003_triggers', 'share')
            m.dependencies = [('share', '0002_create_share_user')]
        else:
            ml = MigrationLoader(connection=connection)
            ml.build_graph()
            last_share_migration = [x[1] for x in ml.graph.leaf_nodes() if x[0] == 'share'][0]
            next_number = '{0:04d}'.format(int(last_share_migration[0:4]) + 1)
            m = Migration('{}_update_trigger_migrations_{}'.format(next_number, datetime.datetime.now().strftime("%Y%m%d_%H%M")), 'share')
            m.dependencies = [('share', '0002_create_share_user'), ('share', last_share_migration)]
        m.operations = ops
        self.write_migration(m)

    def add_arguments(self, parser):
        parser.add_argument('--initial', action='store_true', help='Create initial trigger migrations')
        parser.add_argument('--update', action='store_true', help='Update trigger migrations after schema change')
