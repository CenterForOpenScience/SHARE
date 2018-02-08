import random
import string
import pendulum

from django.db.models import Q

from share.models import WorkIdentifier, Preprint, ShareUser

from share.management.commands import BaseShareCommand
from share.util import IDObfuscator


class Command(BaseShareCommand):

    LIMIT = 250
    OTHER_PROVIDERS = ['arXiv']
    AGGREGATORS = ['DataCite MDS', 'CrossRef']

    def add_arguments(self, parser):
        parser.add_argument('--commit', action='store_true', help='Should the script actually commit?')
        parser.add_argument('--dry', action='store_true', help='Should the script actually make changes? (In a transaction)')
        parser.add_argument('--osf-only', action='store_true', help='Should the script limit to works from OSF sources?')
        parser.add_argument('--limit', type=int, default=self.LIMIT, help='Maximum number of works to fix')
        parser.add_argument('--from', type=lambda d: pendulum.from_format(d, '%Y-%m-%d'), help='Only consider works modified on or after this date')
        parser.add_argument('--until', type=lambda d: pendulum.from_format(d, '%Y-%m-%d'), help='Only consider works modified on or before this date')

    def handle(self, *args, **options):
        with self.rollback_unless_commit(options.get('commit')):
            self.stdout.write(self.style.SUCCESS('Entered Transaction'))

            graveyard = WorkIdentifier.objects.get(uri='http://osf.io/8bg7d/').creative_work
            self.stdout.write(self.style.SUCCESS('Found the Graveyard @ "{}"'.format(graveyard.id)))

            source_query = Q(source__canonical=True)
            if not options.get('osf_only'):
                source_query |= Q(source__long_title__in=self.OTHER_PROVIDERS)

            original_source_ids = set(ShareUser.objects.filter(source_query).values_list('id', flat=True))

            aggregator_source_ids = ShareUser.objects.filter(source__long_title__in=self.AGGREGATORS).values_list('id', flat=True)

            pps = Preprint.objects.filter(
                sources__in=aggregator_source_ids,
                id__in=Preprint.objects.filter(sources__in=original_source_ids)
            )
            if options.get('from'):
                pps = pps.filter(date_modified__gte=options.get('from'))
            else:
                pps = pps.filter(date_modified__gte='2017-07-30')

            if options.get('until'):
                pps = pps.filter(date_modified__lte=options.get('until'))

            limit = options.get('limit')
            i = 0
            for work in pps.iterator():
                if i >= limit:
                    self.stdout.write(self.style.SUCCESS('Fixed {} works, but there might be more. Stopping...'.format(i)))
                    break

                dupes = {}

                for agent in work.related_agents.filter(type='share.person').include('identifiers', 'sources', 'sources__source', 'work_relations'):
                    if not (agent.given_name and agent.family_name):
                        continue
                    dupes.setdefault((agent.given_name, agent.family_name), []).append(agent)

                # Filter down to just duplicated agents
                for k in list(dupes.keys()):
                    if len(dupes[k]) < 2:
                        del dupes[k]

                # If there are no dupes, we have nothing todo
                if not dupes:
                    continue

                i += 1
                self.stdout.write('=== Processing Work "{}" from {} Modified On {} ==='.format(
                    IDObfuscator.encode(work),
                    [u.source.long_title for u in work.sources.all()],
                    work.date_modified
                ))

                for agents in dupes.values():
                    # Order by # of identifiers and a preference towards original sources
                    core_agent = list(sorted(agents, key=lambda x: (
                        len(original_source_ids.intersection([s.id for s in x.sources.all()])),
                        len(x.identifiers.all()),
                        len(x.work_relations.all()),
                    ), reverse=True))[0]

                    self.stdout.write('\tSmashing {} into {} from {} identified by {}'.format(
                        [a for a in agents if a != core_agent],
                        core_agent,
                        # core_agent.sources.values_list('source__long_title', flat=True),
                        # core_agent.identifiers.values_list('uri', flat=True),
                        [user.source.long_title for user in core_agent.sources.all()],
                        [identifier.uri for identifier in core_agent.identifiers.all()]
                    ))

                    for agent in agents:
                        if agent == core_agent:
                            continue
                        for identifier in agent.identifiers.all():
                            self.stdout.write('\t\tRepointing {}: {} -> {}'.format(identifier.uri, agent, core_agent))
                            if not options.get('dry'):
                                identifier.administrative_change(agent=core_agent)

                        for rel in agent.work_relations.all():
                            if rel.creative_work_id != work.id:
                                continue
                            self.stdout.write('\t\tReassigning {}: {} -> {}'.format(rel, IDObfuscator.encode(rel.creative_work), IDObfuscator.encode(graveyard)))
                            if not options.get('dry'):
                                rel.administrative_change(creative_work=graveyard, type=''.join(random.sample(string.ascii_letters, 5)))

                    self.stdout.write(self.style.SUCCESS('\tSuccessfully Processed Agent "{}"'.format(IDObfuscator.encode(agent))))
                self.stdout.write('Bumping last_modified on work')
                if not options.get('dry'):
                    work.administrative_change(allow_empty=True)
                self.stdout.write(self.style.SUCCESS('Successfully Processed Work "{}"\n'.format(IDObfuscator.encode(work))))
            else:
                # Did not break
                self.stdout.write(self.style.SUCCESS('Fixed {} works, and that\'s all!'.format(i)))
