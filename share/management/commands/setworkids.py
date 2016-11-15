import yaml
import argparse

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection
from django.db import transaction

from share.models import AbstractCreativeWork
from share.normalize.links import IRILink, Context


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('id_file', type=argparse.FileType('r'), help='YAML file with a map from work ID to source IDs')

    def handle(self, id_file, *args, **options):
        id_map = yaml.load(id_file)

        temp_id_query = 'select nextval(%s);'

        fk_query = '''
            SELECT kcu.table_name, kcu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.constraint_column_usage AS ccu
                USING (constraint_schema, constraint_name)
            JOIN information_schema.key_column_usage AS kcu
                USING (constraint_schema, constraint_name)
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND ccu.table_name = %s
                AND ccu.column_name = %s;
        '''

        work_id_query = '''
            SELECT DISTINCT wi.creative_work_id
            FROM share_workidentifier wi
            WHERE wi.uri IN %s;
        '''

        with transaction.atomic():
            with connection.cursor() as c:
                c.execute(temp_id_query, ['share_creativework_id_seq'])
                temp_id = c.fetchone()[0]

                c.execute(fk_query, ['share_creativework', 'id'])
                foreign_keys = c.fetchall()

                tables = ['share_creativework', *[t for t, _ in foreign_keys]]

                self.disable_triggers(c, tables)

                for new_id, identifiers in id_map.items():
                    uris = []
                    for app_label, identifier in identifiers:
                        Context().config = apps.get_app_config(app_label)
                        uris.append(IRILink(urn_fallback=True).execute(identifier)['IRI'])
                    c.execute(work_id_query, [tuple(uris)])

                    old_id = c.fetchone()
                    if old_id:
                        old_id = old_id[0]
                        if old_id == new_id:
                            continue
                        print('Moving {} to {}...'.format(old_id, new_id))
                        if AbstractCreativeWork.objects.filter(id=new_id).exists():
                            self.update_id(c, new_id, temp_id, foreign_keys)
                            self.update_id(c, old_id, new_id, foreign_keys)
                            self.update_id(c, temp_id, old_id, foreign_keys)
                        else:
                            self.update_id(c, old_id, new_id, foreign_keys)
                    else:
                        print('Skipping {}! No work found for identifiers: {}'.format(new_id, identifiers))

        # Cannot update a table and then alter it in the same transaction
        with transaction.atomic():
            with connection.cursor() as c:
                self.enable_triggers(c, tables)

    def update_id(self, cursor, old_id, new_id, foreign_keys):
        query = 'UPDATE share_creativework SET id = %s WHERE id = %s;'
        cursor.execute(query, [new_id, old_id])

        fk_query = 'UPDATE {t} SET {c} = %s where {c} = %s;'
        for table, column in foreign_keys:
            cursor.execute(fk_query.format(t=table, c=column), [new_id, old_id])

    def disable_triggers(self, cursor, tables):
        query = 'ALTER TABLE {} DISABLE TRIGGER USER;'
        for table in tables:
            cursor.execute(query.format(table))

    def enable_triggers(self, cursor, tables):
        query = 'ALTER TABLE {} ENABLE TRIGGER USER;'
        for table in tables:
            cursor.execute(query.format(table))
