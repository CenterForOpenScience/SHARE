import argparse
import csv
import glob
import json

from django.core.management.base import BaseCommand

from share.models import Subject, SubjectSynonym


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('subject-file', type=argparse.FileType('r'), help='CSV file of PLOS subject area taxonomy')
        parser.add_argument('--max-depth', type=int, default=12, help='Number of tiers of the taxonomy to include')

    def handle(self, *args, **options):
        subjects = self.parse_subjects(options['subject-file'], options['max_depth'])
        self.stdout.write(json.dumps(subjects, indent=4))

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
        for line in subjects:
            lineage = [n for n in line if n]
            name = lineage.pop()
            if name not in unique_subjects:
                unique_subjects[name] = {
                    'name': name,
                    'parents': [],
                    'lineages': [],
                }
            if lineage:
                unique_subjects[name]['lineages'].append(lineage)
                if unique_subjects[lineage[-1]]['name'] not in unique_subjects[name]['parents']:
                    unique_subjects[name]['parents'].append(unique_subjects[lineage[-1]]['name'])

        return list(unique_subjects.values())
