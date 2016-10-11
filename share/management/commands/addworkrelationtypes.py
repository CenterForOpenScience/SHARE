import argparse
import json

from django.core.management.base import BaseCommand
from django.db import connection
from django.db import transaction

from share.models import WorkRelationType


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('types-file', type=argparse.FileType('r'), help='JSON file of relation types')

    def handle(self, *args, **options):
        self.stdout.write('Loading work relation types...')
        types = json.load(options['types-file'])

        self.stdout.write('Saving {} work relation types...'.format(len(types)))
        self.save_relation_types(types)

    @transaction.atomic
    def save_relation_types(self, types):
        type_map = {}
        for t in types:
            parent = t['parent']
            if parent in type_map:
                t['parent'] = type_map[parent]
            rt = WorkRelationType(**t)
            rt.save()
            type_map[rt.name] = rt.id
