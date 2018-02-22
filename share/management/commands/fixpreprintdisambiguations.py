from celery import states
import pendulum

from share.disambiguation import MergeError
from share.models import CeleryTaskResult, Source, AbstractCreativeWork
from share.tasks import disambiguate
from share.management.commands import BaseShareCommand


class Command(BaseShareCommand):
    MAX_RETRIES = 10
    META_FIXED_KEY = '_fixed'

    def add_arguments(self, parser):
        parser.add_argument('--dry', action='store_true', help='Should the script actually make changes? (In a transaction)')
        parser.add_argument('--commit', action='store_true', help='Should the script actually commit?')
        parser.add_argument('--from', type=lambda d: pendulum.from_format(d, '%Y-%m-%d'), help='Only consider jobs on or after this date')
        parser.add_argument('--until', type=lambda d: pendulum.from_format(d, '%Y-%m-%d'), help='Only consider jobs on or before this date')

    def handle(self, *args, **options):
        dry_run = options.get('dry')

        canonical_sources = list(Source.objects.filter(canonical=True).values_list('long_title', flat=True))
        qs = CeleryTaskResult.objects.filter(
            task_name='share.tasks.disambiguate',
            status__in=[states.FAILURE, states.RETRY],
            meta__source__in=canonical_sources,
        ).exclude(
            meta__has_key=self.META_FIXED_KEY,
            **{'meta__{}'.format(self.META_FIXED_KEY): True}
        ).order_by('date_created')
        if options.get('from'):
            qs = qs.filter(date_modified__gte=options.get('from'))
        if options.get('until'):
            qs = qs.filter(date_modified__lte=options.get('until'))

        for task in qs:
            with self.rollback_unless_commit(options.get('commit')):
                self.stdout.write('\n\nTask {!r}'.format(task.task_id), style_func=self.style.HTTP_INFO)
                self._try_task(task, dry_run)

    def _try_task(self, task, dry_run):
        normalized_data_id = task.meta['args'][0]
        for i in range(self.MAX_RETRIES):
            self.stdout.write('Attempt {} of {}:'.format(i + 1, self.MAX_RETRIES))
            try:
                disambiguate(normalized_data_id)
            except MergeError as e:
                (_, model, queries) = e.args

                if not self._fix_merge_error(task, model, queries, dry_run):
                    return

                if dry_run:
                    return
                continue
            except Exception as e:
                self.stdout.write('Failed in a way we cant fix:', style_func=self.style.ERROR)
                self.stdout.write(str(e))
                return
            task.meta[self.META_FIXED_KEY] = True
            task.save()
            self.stdout.write('Success!', style_func=self.style.SUCCESS)
            return
        self.stdout.write('Failed to fix after {} tries'.format(self.MAX_RETRIES), style_func=self.style.ERROR)

    def _fix_merge_error(self, task, model, queries, dry_run):
        data = {}
        for q in queries:
            for k, v in q.children:
                data.setdefault(k, []).append(v)

        if len(data) > 1:
            self.stdout.write('MergeError is too complex to be automatically fixed', style_func=self.style.ERROR)
            return False

        self.stdout.write('Trying to correct merge error...', style_func=self.style.NOTICE)

        (field, ids), *_ = data.items()
        field_name, field = field.split('__')
        related_field = model._meta.get_field(field_name)
        qs = related_field.related_model.objects.filter(**{field + '__in': ids})

        conflicts = {}
        for inst in qs:
            conflicts.setdefault(getattr(inst, related_field.remote_field.name), []).append(inst)

        (winner, _), *conflicts = sorted(conflicts.items(), key=lambda x: len(x[1]), reverse=True)
        self.stdout.write('\tMerging extraneous {} into {!r}'.format(model._meta.verbose_name_plural, winner))

        for conflict, evidence in conflicts:
            for inst in evidence:
                self.stdout.write('\t\t{!r}: {!r} -> {!r}'.format(inst, getattr(inst, related_field.remote_field.name), winner))
                if not dry_run:
                    inst.administrative_change(**{related_field.remote_field.name: winner})
            if isinstance(conflict, AbstractCreativeWork) and not conflict.identifiers.exists():
                self.stdout.write('\t\tDeleting {!r}'.format(conflict))
                if not dry_run:
                    conflict.administrative_change(is_deleted=True)

        self.stdout.write('Corrected merge error!', style_func=self.style.SUCCESS)
        return True
