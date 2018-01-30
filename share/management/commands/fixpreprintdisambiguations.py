from pendulum import pendulum

from share.exceptions import MergeRequired
from share.management.commands import BaseShareCommand
from share.models import IngestJob
from share.tasks import ingest


class Command(BaseShareCommand):

    def add_arguments(self, parser):
        parser.add_argument('--dry', action='store_true', help='Should the script actually make changes? (In a transaction)')
        parser.add_argument('--commit', action='store_true', help='Should the script actually commit?')
        parser.add_argument('--from', type=pendulum.parse, help='Only consider jobs since this date')

    def handle(self, *args, **options):
        dry_run = options.get('dry')

        qs = IngestJob.objects.filter(
            error_type='MergeRequired',
            status=IngestJob.STATUS.failed,
            source_config__source__canonical=True
        )

        if options.get('from'):
            qs = qs.filter(date_modified__gte=options.get('from'))

        for job in qs:
            self.stdout.write('\n\nReingesting {!r}'.format(job))

            with self.rollback_unless_commit(options.get('commit')):
                try:
                    ingest(job_id=job.id)
                except MergeRequired as e:
                    (_, model, queries) = e.args
                    data = {}
                    for q in queries:
                        for k, v in q.children:
                            data.setdefault(k, []).append(v)

                    if len(data) > 1:
                        self.stdout.write('Merge error from {!r} is too complex to be automatically fixed'.format(
                            job,
                        ), style_func=self.style.ERROR)
                        continue

                    self.stdout.write('Correcting merge error from "{!r}"'.format(job), style_func=self.style.NOTICE)

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

                    self.stdout.write('Corrected merge error from {!r}'.format(job), style_func=self.style.SUCCESS)
                except Exception as e:
                    self.stdout.write('{!r} failed in a way we cant fix:'.format(job), style_func=self.style.ERROR)
                    self.stdout.write('    > {}'.format(e))
