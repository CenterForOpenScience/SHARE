import glob
import json

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        self.stdout.write('Loading synonyms...')

        count = 0

        synonyms = {}
        with open(settings.SUBJECT_SYNONYMS_JSON) as fobj:
            for subject in json.load(fobj):
                synonyms[subject['name'].lower().strip()] = [subject['name']]

        for filename in glob.glob('providers/**/subject-mapping.json', recursive=True):
            self.stdout.write('Loading {}...'.format(filename))

            with open(filename, 'r') as fobj:
                for key, value in json.load(fobj).items():
                    for syn in value:
                        synonyms.setdefault(syn.lower().strip(), []).append(key)
                        count += 1

        with open('share/models/synonyms.json', 'w') as fobj:
            json.dump(synonyms, fobj, indent=4)

        self.stdout.write('Loaded {} synonyms into synonyms.json'.format(count))
