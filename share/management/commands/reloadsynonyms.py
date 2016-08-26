import glob
import json
import shelve

from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        self.stdout.write('Loading synonyms...')

        count = 0
        with shelve.open('synonyms.shelf') as shelf:

            for filename in glob.glob('providers/**/subject-mapping.json', recursive=True):
                self.stdout.write('Loading {}...'.format(filename))

                with open(filename, 'r') as fobj:
                    for key, value in json.load(fobj).items():
                        shelf[key.lower()] = shelf.get(key.lower(), []) + [value]
                        count += 1

        self.stdout.write('Loaded {} synonyms into synonyms.shelf'.format(count))
