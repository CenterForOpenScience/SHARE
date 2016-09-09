import argparse
import json

from django.core.management.base import BaseCommand
from django.db import connection
from django.db import transaction

from share.models import RelationType


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('relation-type-file', type=argparse.FileType('r'), help='JSON file of relation types')

    def handle(self, *args, **options):
        self.stdout.write('Loading relation types...')
        relationTypes = json.load(options['relation-type-file'])

        self.stdout.write('Saving {} relation types...'.format(len(relationTypes)))
        self.save_relation_types(relationTypes)

    @transaction.atomic
    def save_relation_types(self, relationTypes):
        values = [
            (s['key'], s['uri'])
            for s in relationTypes
        ]

        query = 'INSERT INTO {table} ({key}, {uri}) VALUES {values} ON CONFLICT ({key}) DO UPDATE SET {uri} = EXCLUDED.{uri};'.format(
            table=RelationType._meta.db_table,
            key=RelationType._meta.get_field('key').column,
            uri=RelationType._meta.get_field('uri').column,
            values=', '.join(['(%s, %s)'] * len(values)),
        )

        with connection.cursor() as c:
            c.execute(query, [v for vs in values for v in vs])
