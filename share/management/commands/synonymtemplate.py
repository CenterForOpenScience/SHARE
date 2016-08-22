import argparse
import csv
import json

from django.core.management.base import BaseCommand

from share.models import Subject, SubjectSynonym

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('subject-file', type=argparse.FileType('r'), help='CSV file of PLOS subject area taxonomy')
        parser.add_argument('out-file', type=argparse.FileType('w'), help='Output file to write JSON template for synonym mapping')
        parser.add_argument('--max-depth', type=int, default=12, help='Number of tiers of the taxonomy to include')

    def handle(self, *args, **options):
        self.stdout.write('Loading subjects...')
        subjects = self.parse_subjects(options['subject-file'], options['max_depth'])

        self.stdout.write('Writing template for {} unique subjects...'.format(len(subjects)))
        self.write_template(subjects, options['out-file'])

        self.stdout.write('Done!')

    def parse_subjects(self, subject_file, max_depth):
        # Super weird data.
        # Tier 1, Tier 2, Tier 3, ...
        # TOP   ,       ,       , ...
        #       , NEXT  ,       , ...
        #       , NEXT  ,       , ...
        #       ,       , NEXT  , ...
        # TOP   ,       ,       , ...
        with subject_file:
            lines = list(csv.reader(subject_file.readlines()))[1:]
        subjects = [l[:max_depth] for l in lines if any(l[:max_depth])]
        
        # Transform into
        # TOP   , NEXT  , NEXT  , ...
        # TOP   , NEXT  , NEXT  , ...
        # TOP   , NEXT  , NEXT  , ...
        # TOP   , NEXT  , NEXT  , ...
        # TOP   , NEXT  , NEXT  , ...
        for i, line in enumerate(subjects):
            tier, name = next((t, n) for (t, n) in reversed(list(enumerate(line))) if n)

            for other in subjects[i + 1:]:
                if other[tier] or (tier > 0 and other[tier - 1] != line[tier - 1]):
                    break
                other[tier] = name

        unique_subjects = {}
        next_id = 1
        for line in subjects:
            lineage = [n for n in line if n]
            name = lineage.pop()
            if name not in unique_subjects:
                unique_subjects[name] = {
                    'pk': next_id,
                    'name': name,
                    'lineages': [],
                }
                next_id = next_id + 1
            if lineage:
                unique_subjects[name]['lineages'].append(lineage)

        return sorted(unique_subjects.values(), key=lambda s: s['pk'])

    def write_template(self, subjects, out_file):
        names = sorted([s['name'] for s in subjects])
        out_file.write('{\n')
        for i, n in enumerate(names):
            out_file.write('    "{}": []{}\n'.format(n, ',' if i < len(names)-1 else ''))
        out_file.write('}\n')

