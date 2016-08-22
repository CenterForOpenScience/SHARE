import argparse
import json
import os

from django.apps import apps
from django.core.management.base import BaseCommand

from share.models import Subject, SubjectSynonym
from share.provider import ProviderAppConfig

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Load synonyms for all sources')
        parser.add_argument('source', nargs='*', type=str, help='The name of the source to load synonyms from')
        parser.add_argument('--file', type=argparse.FileType('r'), help='JSON dictionary of subject synonyms')

    def handle(self, *args, **options):
        synonyms = {}
        if options['file']:
            print('Collecting synonyms from file...')
            self.collect_synonyms(options['file'], synonyms)

        if not options['source'] and options['all']:
            options['source'] = [x.label for x in apps.get_app_configs() if isinstance(x, ProviderAppConfig) and not x.disabled]

        for source in options['source']:
            app_config = apps.get_app_config(source)
            synonym_file = os.path.join(app_config.path, 'subject-mapping.json')
            if not os.path.isfile(synonym_file):
                continue

            print('Collecting subject synonyms from {}...'.format(source))
            with open(synonym_file) as fobj:
                self.collect_synonyms(fobj, synonyms)

        self.insert_new_synonyms(synonyms)

    def collect_synonyms(self, file, synonyms):
        for subject, syns in json.load(file).items():
            if subject not in synonyms:
                synonyms[subject] = set()
            synonyms[subject].update(syns)

    def insert_new_synonyms(self, synonyms):
        subjects = { name: id for name, id in Subject.objects.values_list('name', 'id') }
        existing_synonyms = {}
        for sub, syn in SubjectSynonym.objects.values_list('subject__name', 'synonym'):
            if sub not in existing_synonyms:
                existing_synonyms[sub] = set()
            existing_synonyms[sub].add(syn)

        for sub, syn in synonyms.items():
            if sub in existing_synonyms:
                syn -= existing_synonyms[sub]

        to_create = [
            SubjectSynonym(subject_id=subjects[sub], synonym=syn)
            for sub, syn_set in synonyms.items()
            for syn in syn_set
        ]
        if to_create:
            print('Creating {} new synonyms...'.format(len(to_create)))
            SubjectSynonym.objects.bulk_create(to_create)
        else:
            print('No new synonyms found.')
