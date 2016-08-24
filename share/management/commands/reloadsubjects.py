import argparse
import csv
import json

from django.core.management.base import BaseCommand

from share.models import Subject, SubjectSynonym

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('subject-file', type=argparse.FileType('r'), help='CSV file of PLOS subject area taxonomy')
        parser.add_argument('synonym-file', type=argparse.FileType('r'), help='CSV file of PLOS subject area synonyms')
        parser.add_argument('--max-depth', type=int, default=12, help='Number of tiers of the taxonomy to include')

    def handle(self, *args, **options):
        self.stdout.write('Loading synonyms...')
        synonyms = self.parse_synonyms(options['synonym-file'])
        synonyms_count = sum(len(s) for s in synonyms.values())

        self.stdout.write('Loading subjects...')
        subjects = self.parse_subjects(options['subject-file'], options['max_depth'], synonyms)

        self.stdout.write('Saving {} unique subjects and {} synonyms...'.format(len(subjects), synonyms_count))
        self.reload_subjects(subjects)

        self.stdout.write('Done!')

    def reload_subjects(self, subjects):
        Subject.objects.all().delete()

        Subject.objects.bulk_create([
            Subject(pk=sub['pk'], name=sub['name'], lineages=sub['lineages'])
            for sub in subjects
        ])

        Subject.parents.through.objects.bulk_create([
            Subject.parents.through(from_subject_id=sub['pk'], to_subject_id=parent)
            for sub in subjects
            for parent in sub['parents']
        ])

        SubjectSynonym.objects.bulk_create([
            SubjectSynonym(subject_id=sub['pk'], synonym=syn)
            for sub in subjects
            for syn in sub['synonyms']
        ])

    def parse_subjects(self, subject_file, max_depth, synonyms):
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
                    'parents': [],
                    'lineages': [],
                    'synonyms': synonyms[name] if name in synonyms else []
                }
                next_id = next_id + 1
            if lineage:
                unique_subjects[name]['lineages'].append(lineage)
                if unique_subjects[lineage[-1]]['pk'] not in unique_subjects[name]['parents']:
                    unique_subjects[name]['parents'].append(unique_subjects[lineage[-1]]['pk'])

        return sorted(unique_subjects.values(), key=lambda s: s['pk'])

    def parse_synonyms(self, synonym_file):
        # Stored As
        # TAG1  Synonym1
        # TAG1  Synonym2
        # TAG2
        # TAG3  Synonym1
        # TAG4  Synonym1
        # ...
        synonyms = {}
        with synonym_file:
            lines = list(csv.reader(synonym_file.readlines()))[1:]

        for term, sym in lines:
            if not sym:
                continue  # No Synonym exists
            if term not in synonyms:
                synonyms[term] = set()
            synonyms[term].add(sym)

        return synonyms
