import json

import argparse

from django.core.management.base import BaseCommand
from django.db import connection
from django.db import transaction

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('out_file', type=argparse.FileType('w'), help='Output file for json map of source ids')
        parser.add_argument('work_ids', nargs='*', type=int, help='The id(s) of the creative works to migrate')

    def handle(self, out_file, work_ids, *args, **options):

        query = '''
        SELECT DISTINCT acw.id, rd.provider_doc_id FROM
          share_rawdata AS rd
          JOIN share_normalizeddata AS nd ON rd.id = nd.raw_id
          JOIN share_changeset AS cs ON nd.id = cs.normalized_data_id
          JOIN share_change AS c ON cs.id = c.change_set_id
          JOIN share_abstractcreativework AS acw ON c.id = acw.change_id
          WHERE acw.id IN %s AND acw.title != '' AND c.change->>'title' = acw.title
          ORDER BY acw.id;
        '''

        with connection.cursor() as c:
            c.execute(query, (tuple(work_ids),))

            source_ids = {}
            data = c.fetchone()
            while data:
                (id, source_id) = data
                try:
                    source_ids[id].append(source_id)
                except KeyError:
                    source_ids[id] = [source_id]
                data = c.fetchone()

        json.dump(source_ids, out_file, indent=4)
