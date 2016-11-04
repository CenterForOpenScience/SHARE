import argparse
import json

from django.core.management.base import BaseCommand
from django.db import connection
from django.db import transaction

from share.models import Subject


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('subject-file', type=argparse.FileType('r'), help='JSON file of subjects')

    def handle(self, *args, **options):
        self.stdout.write('Loading subjects...')
        subjects = json.load(options['subject-file'])

        self.stdout.write('Saving {} unique subjects...'.format(len(subjects)))
        self.save_subjects(subjects)

    @transaction.atomic
    def save_subjects(self, subjects):
        name_pk = {s['name']: i for i, s in enumerate(subjects)}
        name_pk[None] = None

        with transaction.atomic(), connection.cursor() as c:
            c.execute('INSERT INTO {table} (id, {name}, {parent}) VALUES {values} ON CONFLICT ({name}) DO NOTHING;'.format(
                table=Subject._meta.db_table,
                name=Subject._meta.get_field('name').column,
                parent=Subject._meta.get_field('parent').column,
                values=', '.join(['%s'] * len(subjects)),
            ), [(i, s['name'], name_pk[s['parent']]) for i, s in enumerate(subjects)])
