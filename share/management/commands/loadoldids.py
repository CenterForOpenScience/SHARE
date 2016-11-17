import json
import argparse

from django.core.management.base import BaseCommand
from django.db import connection
from django.db import transaction

from share.normalize.tools import IRILink


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('old_id_file', type=argparse.FileType('r'), help='JSON file with a map from work ID to source IDs')

    def handle(self, old_id_file, *args, **options):
        id_map = json.load(old_id_file)
        iri = IRILink(urn_fallback=True)
        identifiers = [(id, iri.execute(uri)) for (id, uris) in id_map.items() for uri in uris]

        works_query = '''
            ALTER TABLE share_creativework ALTER COLUMN change_id DROP NOT NULL;
            ALTER TABLE share_creativework ALTER COLUMN version_id DROP NOT NULL;

            INSERT INTO share_creativework (type, id, title, description, is_deleted, free_to_read_type, date_created, date_modified)
            VALUES {work_values};
        '''.format(
            work_values=','.join(["('share.creativework', %s, '', '', false, '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"] * len(id_map))
        )
        print(works_query)

        identifiers_query = '''
            ALTER TABLE share_workidentifier ALTER COLUMN change_id DROP NOT NULL;
            ALTER TABLE share_workidentifier ALTER COLUMN version_id DROP NOT NULL;
            ALTER TABLE share_workidentifier ALTER COLUMN creative_work_version_id DROP NOT NULL;

            INSERT INTO share_workidentifier (creative_work_id, uri, host, scheme, date_created, date_modified)
            VALUES {id_values};
        '''.format(
            id_values=','.join(["(%s, %s, '', '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"] * len(identifiers))
        )
        print(identifiers_query)

        with transaction.atomic():
            with connection.cursor() as c:
                c.execute('SET session_replication_role = replica;')
                c.execute(works_query, tuple(id_map.keys()))
                c.execute(identifiers_query, [v for pair in identifiers for v in pair])
                c.execute('SET session_replication_role = DEFAULT;')
