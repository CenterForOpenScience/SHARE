from celery import states

from django.core.management.base import BaseCommand
from django.db import transaction

from share.disambiguation import MergeError
from share.models import CeleryTaskResult
from share.tasks import disambiguate


class Command(BaseCommand):

    OSF_PP = [
        'AgriXiv',
        'BITSS',
        'INA-Rxiv',
        'LIS Scholarship Archive',
        'LawArXiv',
        'MindRxiv',
        'NutriXiv',
        'Open Science Framework',
        'PaleorXiv',
        'PsyArXiv',
        'SocArXiv',
        'SportRxiv',
        'Thesis Commons',
        'engrXiv',
    ]

    def add_arguments(self, parser):
        parser.add_argument('--dry', action='store_true', help='Should the script actually make changes? (In a transaction)')

    def handle(self, *args, **options):
        qs = CeleryTaskResult.objects.filter(
            task_name='share.tasks.disambiguate',
            status=states.FAILURE,
            meta__source__in=self.OSF_PP
        )

        for task in qs:
            self.stdout.write('Running {!r}'.format(task.meta['args'][0]))
            try:
                disambiguate(task.meta['args'][0])
            except MergeError as e:
                self.stdout.write('Correcting merge error from {!r}'.format(task.meta['args'][0]), style_func=self.style.NOTICE)
                (_, model, queries) = e.args
                data = {}
                for q in queries:
                    assert len(q.children) == 1
                    k, v = q.children[0]
                    data.setdefault(k, []).append(v)

                assert len(data) == 1
                (field, ids), *_ = data.items()
                field_name, field = field.split('__')

                related_field = model._meta.get_field(field_name)
                qs = related_field.related_model.objects.filter(**{field + '__in': ids})

                conflicts = {}
                for inst in qs:
                    conflicts.setdefault(getattr(inst, related_field.remote_field.name), []).append(inst)

                (winner, _), *conflicts = sorted(conflicts.items(), key=lambda x: len(x[1]), reverse=True)
                self.stdout.write('\tMerging extranious {} into {!r}'.format(model._meta.verbose_name_plural, winner))

                with transaction.atomic():
                    for conflict, evidence in conflicts:
                        for inst in evidence:
                            self.stdout.write('\t\t{!r}: {!r} -> {!r}'.format(inst, getattr(inst, related_field.remote_field.name), winner))
                            if not self.options.get('dry'):
                                inst.administrative_change(**{related_field.remote_field.name: winner})
                    self.stdout.write('Corrected merge error from {!r}'.format(task.meta['args'][0]), style_func=self.style.SUCCESS)
                    self.stdout.write('\n\n')
            except Exception as e:
                self.stdout.write('{!r} failed in a way we cant fix'.format(task.meta['args'][0]), style_func=self.style.WARNING)
