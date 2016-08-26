import argparse
import json

from django.core.management.base import BaseCommand
from django.db import connection

from share.models import Subject


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('subject-file', type=argparse.FileType('r'), help='JSON file of subjects')

    def handle(self, *args, **options):
        self.stdout.write('Loading subjects...')
        subjects = json.load(options['subject-file'])

        self.stdout.write('Saving {} unique subjects...'.format(len(subjects)))
        self.save_subjects(subjects)

    def save_subjects(self, subjects):
        subjects_values = [
            (s['name'], json.dumps(s['lineages']))
            for s in subjects
        ]

        subjects_query = 'INSERT INTO {table} ({name}, {lineages}) VALUES {values} ON CONFLICT ({name}) DO NOTHING;'.format(
            table=Subject._meta.db_table,
            name=Subject._meta.get_field('name').column,
            lineages=Subject._meta.get_field('lineages').column,
            values=', '.join(['(%s, %s)'] * len(subjects_values)),
        )

        with connection.cursor() as c:
            c.execute(subjects_query, [v for vs in subjects_values for v in vs])

        subject_ids = {name: id for (name, id) in Subject.objects.all().values_list('name', 'id')}

        parents_values = [
            (subject_ids[s['name']], subject_ids[parent])
            for s in subjects
            for parent in s['parents']
        ]

        parents_query = 'INSERT INTO {table} ({subject}, {parent}) VALUES {values} ON CONFLICT ({subject}, {parent}) DO NOTHING;'.format(
            table=Subject.parents.through._meta.db_table,
            subject=Subject.parents.through._meta.get_field('from_subject').column,
            parent=Subject.parents.through._meta.get_field('to_subject').column,
            values=', '.join(['(%s, %s)'] * len(parents_values)))

        with connection.cursor() as c:
            c.execute(parents_query, [v for vs in parents_values for v in vs])
