import argparse
import json

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from share.util import TopographicalSorter


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('type-model', type=str, help='Relation type model')
        parser.add_argument('types-file', type=argparse.FileType('r'), help='JSON file of relation types')

    def handle(self, *args, **options):
        model_name = options['type-model']
        type_model = apps.get_model('share', model_name)

        self.stdout.write('Loading {}s from {}...'.format(model_name, options['types-file'].name))
        types = json.load(options['types-file'])

        self.stdout.write('Saving {} {}s...'.format(len(types), model_name))
        self.save_relation_types(type_model, types)

    @transaction.atomic
    def save_relation_types(self, type_model, types):
        sorter = TopographicalSorter(types, dependencies=lambda t: [t['parent']], key=lambda t: t['name'])
        type_ids = {}
        for t in sorter.sorted():
            parent = t.pop('parent')
            if parent in type_ids:
                t['parent_id'] = type_ids[parent]
            (rt, _) = type_model.objects.update_or_create(name=t['name'], defaults=t)
            type_ids[rt.name] = rt.id
