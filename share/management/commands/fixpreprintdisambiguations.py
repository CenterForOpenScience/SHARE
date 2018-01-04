from celery import states
import pendulum

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from share.disambiguation import MergeError
from share.models import CeleryTaskResult
from share.tasks import disambiguate


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--dry', action='store_true', help='Should the script actually make changes? (In a transaction)')
        parser.add_argument('--commit', action='store_true', help='Should the script actually commit?')
        parser.add_argument('--from', type=lambda d: pendulum.from_format(d, '%Y-%m-%d'), help='Only consider jobs since this date')

    def handle(self, *args, **options):
        qs = CeleryTaskResult.objects.filter(
            task_name='share.tasks.disambiguate',
            status__in=[states.FAILURE, states.RETRY],
            meta__source__in=settings.OSF_PREPRINT_PROVIDERS,
        )
        if options.get('from'):
            qs = qs.filter(date_modified__gte=options.get('from'))

        for task in qs:
            self.stdout.write('\n\nRunning {!r}'.format(task.task_id))
            try:
                with transaction.atomic():
                    try:
                        disambiguate(task.meta['args'][0])
                    except MergeError as e:
                        (_, model, queries) = e.args
                        data = {}
                        for q in queries:
                            for k, v in q.children:
                                data.setdefault(k, []).append(v)

                        if len(data) > 1:
                            self.stdout.write('MergeError from NormalizedData "{}" in task "{}" is too complex to be automatically fixed'.format(
                                task.meta['args'][0],
                                task.task_id,
                            ), style_func=self.style.ERROR)
                            continue

                        self.stdout.write('Correcting merge error from "{!r}"'.format(task.meta['args'][0]), style_func=self.style.NOTICE)

                        (field, ids), *_ = data.items()
                        field_name, field = field.split('__')
                        related_field = model._meta.get_field(field_name)
                        qs = related_field.related_model.objects.filter(**{field + '__in': ids})

                        conflicts = {}
                        for inst in qs:
                            conflicts.setdefault(getattr(inst, related_field.remote_field.name), []).append(inst)

                        (winner, _), *conflicts = sorted(conflicts.items(), key=lambda x: len(x[1]), reverse=True)
                        self.stdout.write('\tMerging extranious {} into {!r}'.format(model._meta.verbose_name_plural, winner))

                        for conflict, evidence in conflicts:
                            for inst in evidence:
                                self.stdout.write('\t\t{!r}: {!r} -> {!r}'.format(inst, getattr(inst, related_field.remote_field.name), winner))
                                if not options.get('dry'):
                                    inst.administrative_change(**{related_field.remote_field.name: winner})

                        self.stdout.write('Corrected merge error from {!r}'.format(task.meta['args'][0]), style_func=self.style.SUCCESS)
                    except Exception as e:
                        self.stdout.write('{!r} failed in a way we cant fix'.format(task.meta['args'][0]), style_func=self.style.ERROR)

                    if not options.get('commit'):
                        self.stdout.write('Rollback changes', style_func=self.style.NOTICE)
                        raise AssertionError('ROLLBACK')

            except AssertionError as e:
                if e.args != ('ROLLBACK', ):
                    raise
