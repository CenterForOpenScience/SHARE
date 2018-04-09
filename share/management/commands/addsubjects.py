import yaml

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction

from share.models import ShareUser, SubjectTaxonomy
from share.ingest.ingester import Ingester


class Command(BaseCommand):

    def handle(self, *args, **options):
        with open(settings.SUBJECTS_YAML) as fobj:
            subjects = yaml.load(fobj)

        self.save_subjects(subjects)

    @transaction.atomic
    def save_subjects(self, subjects):
        # Ensure central taxonomy exists
        user = ShareUser.objects.get(username=settings.APPLICATION_USERNAME)
        SubjectTaxonomy.objects.get_or_create(source=user.source)

        subjects = [
            {
                '@id': '_:{}'.format(s['uri']),
                '@type': 'subject',
                'name': s['name'],
                'uri': s['uri'],
                'parent': None if s['parent'] is None else {'@id': '_:{}'.format(s['parent']), '@type': 'subject'}
            } for s in subjects
        ]

        Ingester(subjects).as_user(user).ingest()
