import argparse
import json

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction

from share.models import ShareUser, SubjectTaxonomy, NormalizedData
from share.tasks import disambiguate


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
        # Ensure central taxonomy exists
        SubjectTaxonomy.objects.get_or_create(name=settings.SUBJECTS_CENTRAL_TAXONOMY)

        normalized_data = NormalizedData.objects.create(
            source=ShareUser.objects.get(username=settings.APPLICATION_USERNAME),
            data={
                '@graph': [
                    {
                        '@id': '_:{}'.format(s['name']),
                        '@type': 'subject',
                        'name': s['name'],
                        'parent': None if s['parent'] is None else {'@id': '_:{}'.format(s['parent']), '@type': 'subject'}
                    } for s in subjects
                ]
            }
        )
        disambiguate.apply((normalized_data.id,), throw=True)
