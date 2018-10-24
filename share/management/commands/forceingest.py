import random
import string
import pendulum

from django.db.utils import IntegrityError

from share.exceptions import MergeRequired, ShareException
from share.models import AbstractCreativeWork, AbstractAgent
from share.management.commands import BaseShareCommand
from share.models import IngestJob
from share.tasks.jobs import IngestJobConsumer


MAX_RETRIES = 10
GRAVEYARD_IDENTIFIERS = [
    'http://osf.io/8bg7d/',  # prod
    'http://staging.osf.io/8hym9/',  # staging
]


class Command(BaseShareCommand):

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

        graveyard = AbstractCreativeWork.objects.get(identifiers__uri__in=GRAVEYARD_IDENTIFIERS)
        hacky_merger = HackyMerger(dry_run, interactive, graveyard, self)

        for job in qs.select_related('suid', 'source_config'):
            with self.rollback_unless_commit(options.get('commit')):
                self.stdout.write('\n\nTrying job {!r}'.format(job), style_func=self.style.HTTP_INFO)
                self._try_job(job, hacky_merger)

    def _try_job(self, job, hacky_merger):
        for i in range(MAX_RETRIES):
            self.stdout.write('Attempt {} of {}:'.format(i + 1, MAX_RETRIES))
            try:
                IngestJobConsumer().consume(job_id=job.id, exhaust=False)
            except MergeRequired as e:
                (_, *dupe_sets) = e.args

                try:
                    for dupes in dupe_sets:
                        hacky_merger.merge(dupes)
                except RejectMerge:
                    self.stdout.write('Skipping...', style_func=self.style.WARNING)
                    return
                except CannotMerge as e:
                    self.stdout.write('Failed to merge:', style_func=self.style.ERROR)
                    self.stdout.write(str(e))
                    return

                if hacky_merger.dry_run:
                    return
                continue
            except Exception as e:
                self.stdout.write('Failed in a way we cannot fix:', style_func=self.style.ERROR)
                self.stdout.write('\t{!r}'.format(e))
                return
            self.stdout.write('Success!', style_func=self.style.SUCCESS)
            return
        self.stdout.write('Failed to fix after {} tries'.format(MAX_RETRIES), style_func=self.style.ERROR)


class CannotMerge(ShareException):
    pass


class RejectMerge(ShareException):
    pass


class HackyMerger:
    def __init__(self, dry_run, interactive, graveyard, command):
        self.dry_run = dry_run
        self.interactive = interactive
        self.graveyard = graveyard
        self.command = command

    def merge(self, dupes):
        if len(dupes) < 2:
            return

        model = list(dupes)[0]._meta.concrete_model
        if any(d._meta.concrete_model is not model for d in dupes):
            raise CannotMerge('Things in different tables are not dupes: {}'.format(dupes))

        if model is AbstractAgent:
            return self.merge_agents(dupes)
        if model is AbstractCreativeWork:
            return self.merge_works(dupes)
        raise CannotMerge('Cannot merge dupes of type {}'.format(model))

    def merge_agents(self, dupes):
        agents = AbstractAgent.objects.filter(
            id__in=[d.id for d in dupes],
        ).include(
            'identifiers',
            'sources',
            'sources__source',
            'work_relations',
        )

        # Order by # of canonical sources with a preference for more identifiers and relations
        winner, *losers = list(sorted(agents, key=lambda agent: (
            sum(1 for s in agent.sources.all() if s.source.canonical),
            len(agent.identifiers.all()),
            len(agent.work_relations.all()),
        ), reverse=True))

        self.describe_smash(winner, losers)
        if self.interactive and not self.command.input_confirm('OK? (y/n) '):
            raise RejectMerge

        for loser in losers:
            for identifier in loser.identifiers.all():
                if not self.dry_run:
                    identifier.administrative_change(agent=winner)

            for rel in loser.work_relations.all():
                if not self.dry_run:
                    try:
                        rel.administrative_change(agent=winner)
                    except IntegrityError:
                        # OK, to the graveyard instead
                        rel.administrative_change(
                            creative_work=self.graveyard,
                            type=''.join(random.sample(string.ascii_letters, 5))
                        )

    def merge_works(self, dupes):
        works = AbstractCreativeWork.objects.filter(
            id__in=[d.id for d in dupes],
        ).include(
            'identifiers',
            'sources',
            'sources__source',
            'agent_relations',
        )

        # Order by # of canonical sources with a preference for more identifiers and relations
        winner, *losers = list(sorted(works, key=lambda work: (
            sum(1 for user in work.sources.all() if user.source.canonical),
            len(work.identifiers.all()),
            len(work.agent_relations.all()),
        ), reverse=True))

        self.describe_smash(winner, losers)
        if self.interactive and not self.command.input_confirm('OK? (y/n) '):
            return

        for loser in losers:
            for identifier in loser.identifiers.all():
                if not self.dry_run:
                    identifier.administrative_change(creative_work=winner)

            if not self.dry_run:
                loser.administrative_change(is_deleted=True)

    def describe_smash(self, winner, losers):
        self.command.stdout.write('\tSmashing the following:', style_func=self.command.style.WARNING)
        for loser in losers:
            self.command.stdout.write(self.format_agent_or_work(loser))
        self.command.stdout.write('\tinto:', style_func=self.command.style.WARNING)
        self.command.stdout.write(self.format_agent_or_work(winner))

    def format_agent_or_work(self, obj):
        return '\t\t{} ({})'.format(
            obj,
            ', '.join(sorted(
                [i.uri for i in obj.identifiers.all()],
                key=len,
            )),
        )
