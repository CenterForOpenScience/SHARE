import pendulum

from django.db import transaction
from django.db.utils import IntegrityError

from share.disambiguation.criteria import MatchByOneToMany
from share.exceptions import MergeRequired
from share.models import AbstractCreativeWork, AbstractAgent
from share.management.commands import BaseShareCommand
from share.models import IngestJob
from share.tasks.jobs import IngestJobConsumer
from share.util import ensure_iterable


class Command(BaseShareCommand):
    MAX_RETRIES = 10

    def add_arguments(self, parser):
        parser.add_argument('--dry', action='store_true', help='Should the script actually make changes? (In a transaction)')
        parser.add_argument('--commit', action='store_true', help='Should the script actually commit?')
        parser.add_argument('--noninteractive', action='store_true', help='Should the script merge objects without asking?')
        parser.add_argument('--from', type=lambda d: pendulum.from_format(d, '%Y-%m-%d'), help='Only consider jobs on or after this date')
        parser.add_argument('--until', type=lambda d: pendulum.from_format(d, '%Y-%m-%d'), help='Only consider jobs on or before this date')

    def handle(self, *args, **options):
        dry_run = options.get('dry')
        interactive = not options.get('noninteractive')

        qs = IngestJob.objects.filter(
            error_type='MergeRequired',
            status=IngestJob.STATUS.failed,
            source_config__source__canonical=True
        ).order_by('date_created')
        if options.get('from'):
            qs = qs.filter(date_modified__gte=options.get('from'))
        if options.get('until'):
            qs = qs.filter(date_modified__lte=options.get('until'))

        for job in qs.select_related('suid', 'source_config'):
            with self.rollback_unless_commit(options.get('commit')):
                self.stdout.write('\n\nTrying job {!r}'.format(job), style_func=self.style.HTTP_INFO)
                self._try_job(job, dry_run, interactive)

    def _try_job(self, job, dry_run, interactive):
        for i in range(self.MAX_RETRIES):
            self.stdout.write('Attempt {} of {}:'.format(i + 1, self.MAX_RETRIES))
            try:
                IngestJobConsumer().consume(job_id=job.id, exhaust=False)
            except MergeRequired as e:
                (_, *dupe_sets) = e.args

                if not self._fix_merge_error(dupe_sets, dry_run, interactive):
                    return

                if dry_run:
                    return
                continue
            except Exception as e:
                self.stdout.write('Failed in a way we cant fix:', style_func=self.style.ERROR)
                self.stdout.write(str(e))
                return
            self.stdout.write('Success!', style_func=self.style.SUCCESS)
            return
        self.stdout.write('Failed to fix after {} tries'.format(self.MAX_RETRIES), style_func=self.style.ERROR)

    def _fix_merge_error(self, dupe_sets, dry_run, interactive):
        for dupes in dupe_sets:
            if len(dupes) < 2:
                continue
            model = list(dupes)[0]._meta.concrete_model
            if any(d._meta.concrete_model is not model for d in dupes):
                raise ValueError('Cannot merge across tables: {}'.format(dupes))

            if not self._merge_together(model, dupes, dry_run, interactive):
                return False
        return True

    def _merge_together(self, model, dupes, dry_run, interactive):
        criteria = [
            c for c in ensure_iterable(model.matching_criteria)
            if isinstance(c, MatchByOneToMany)
        ]

        if not criteria:
            self.stdout.write('Cannot automatically fix errors on {}, need a MatchByOneToMany criterion'.format(model), style_func=self.style.ERROR)
            return False

        field_name = criteria[0].relation_name
        ret = self._repoint_fks(model._meta.get_field(field_name).remote_field, dupes, dry_run, interactive)

        if not ret:
            return ret

        # special case...
        if model is AbstractAgent:
            return self._repoint_fks(model._meta.get_field('work_relations').remote_field, dupes, dry_run, interactive)
        return True

    def _repoint_fks(self, fk_field, targets, dry_run, interactive):
        ids = [d.id for d in targets]
        qs = fk_field.model.objects.filter(**{fk_field.name + '__in': ids})

        conflicts = {}
        for inst in qs:
            conflicts.setdefault(getattr(inst, fk_field.name), []).append(inst)

        (winner, _), *conflicts = sorted(conflicts.items(), key=lambda x: len(x[1]), reverse=True)

        if not conflicts:
            return True

        self.stdout.write('\tMerging extras into {!r}'.format(winner))
        for conflict, evidence in conflicts:
            for inst in evidence:
                self.stdout.write('\t\t{!r}: {!r} -> {!r}'.format(inst, getattr(inst, fk_field.name), winner))

        if interactive and not self.input_confirm('OK? (y/n) '):
            self.stdout.write('Skipping...', style_func=self.style.WARNING)
            return False

        for conflict, evidence in conflicts:
            if not dry_run:
                for inst in evidence:
                    self._repoint_fk(inst, fk_field, winner)
            if isinstance(conflict, AbstractCreativeWork) and not conflict.identifiers.exists():
                self.stdout.write('\t\tDeleting {!r}'.format(conflict))
                if not dry_run:
                    conflict.administrative_change(is_deleted=True)

        self.stdout.write('Corrected merge error!', style_func=self.style.SUCCESS)
        return True

    def _repoint_fk(self, obj, fk_field, target):
        try:
            with transaction.atomic():
                obj.administrative_change(**{fk_field.name: target})
        except IntegrityError:
            pass
