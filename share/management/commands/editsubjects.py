import argparse
import uuid
import yaml
import json

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction

from share.models import ShareUser, SubjectTaxonomy, NormalizedData
from share.tasks import disambiguate


# input file syntax:
# - new subjects: each on their own line with full lineage separated by |
#   e.g. Subject One|Subject Two|Subject Three
# - rename subjects:
#   e.g. Subject One => Subject 1


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('changes', type=argparse.FileType('r'), help='changes to make')

    def handle(self, *args, **options):
        with open(settings.SUBJECTS_YAML) as f:
            subjects = self.load_subjects(f)

        for change in options['changes'].readlines():
            if not change.strip() or change.startswith('#'):
                continue
            subject_names = change.split('=>')
            if len(subject_names) == 1:
                self.add_subject(subjects, subject_names[0])
            elif len(subject_names) == 2:
                self.rename_subject(subjects, *subject_names)
            else:
                raise ValueError('What is this: {}'.format(change))

        subjects_list = sorted(subjects.values(), key=lambda s: s['name'])
        with open(settings.SUBJECTS_YAML, 'w') as f:
            yaml.dump(subjects_list, f, default_flow_style=False)
        
    def load_subjects(self, fobj):
        subject_list = yaml.load(fobj)
        subject_map = {}
        for s in subject_list:
            if s['name'] in subject_map:
                raise ValueError('Duplicate subject: {}'.format(s['name']))
            if not s.get('uri'):
                s['uri'] = uuid.uuid4().urn
            s['name'] = s['name'].strip()
            subject_map[s['name']] = s
        return subject_map

    def add_subject(self, subjects, lineage):
        if isinstance(lineage, str):
            lineage = [s.strip() for s in lineage.split('|')]
        new_subject = lineage[-1]
        parent = None
        if len(lineage) > 1:
            parent = lineage[-2]
            if parent not in subjects:
                self.add_subject(subjects, lineage[:-1])
        if new_subject in subjects:
            raise ValueError('Duplicate subject: {}'.format(new_subject))
        subjects[new_subject] = {
            'name': new_subject,
            'parent': subjects[parent]['uri'],
            'uri': uuid.uuid4().urn,
        }
        self.stdout.write('Added subject: {}'.format(new_subject))

    def rename_subject(self, subjects, old_name, new_name):
        old_name = old_name.strip()
        new_name = new_name.strip()
        if old_name not in subjects:
            raise ValueError('Unknown subject: {}'.format(old_name))
        if new_name in subjects:
            raise ValueError('Duplicate subject: {}'.format(new_name))
        subjects[old_name]['name'] = new_name
        self.stdout.write('Renamed subject: {} => {}'.format(old_name, new_name))
