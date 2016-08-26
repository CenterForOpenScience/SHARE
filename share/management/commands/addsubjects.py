import argparse
import csv
import glob
import json

from django.core.management.base import BaseCommand

from share.models import Subject, SubjectSynonym


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('subject-file', type=argparse.FileType('r'), help='JSON file of subjects')

    def handle(self, *args, **options):
        self.stdout.write('Loading subjects...')
        subjects = json.load(options['subject-file'])

        self.stdout.write('Saving {} unique subjects...'.format(len(subjects)))
        self.save_subjects(subjects)

    def save_subjects(self, subjects):
        # This is all kinds of inefficient, maybe replace with a bulk upsert written in SQL

        existing_subjects = set(Subject.objects.all().values_list('name', flat=True))

        Subject.objects.bulk_create([
            Subject(name=sub['name'], lineages=sub['lineages'])
            for sub in subjects
            if sub['name'] not in existing_subjects
        ])

        subject_ids = { name: id for (name, id) in
                       Subject.objects.all().values_list('name', 'id') }

        Subject.parents.through.objects.bulk_create([
            Subject.parents.through(from_subject_id=subject_ids[sub['name']], to_subject_id=subject_ids[parent])
            for sub in subjects
            for parent in sub['parents']
            if not Subject.parents.through.objects.filter(from_subject_id=subject_ids[sub['name']], to_subject_id=subject_ids[parent]).exists()
        ])
