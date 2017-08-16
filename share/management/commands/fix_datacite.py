import random
import string

from django.core.management.base import BaseCommand
from django.db import transaction


from share.models import WorkIdentifier, Preprint, ShareUser


class Command(BaseCommand):

    OSF_PP = ['OSF', 'engrXiv', 'PsyArXiv', 'BITSS', 'LIS Scholarship Archive', 'SocArXiv', 'LawArXiv', 'AgriXiv', 'MindRxiv', 'Open Science Framework']
    AGGREGATORS = ['DataCite MDS', 'CrossRef']

    def add_arguments(self, parser):
        parser.add_argument('--commit', action='store_true', help='Should the script actually commit?')
        parser.add_argument('--dry', action='store_true', help='Should the script actually make changes? (In a transaction)')

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write(self.style.SUCCESS('Entered Transaction'))

            graveyard = WorkIdentifier.objects.get(uri='http://osf.io/8bg7d/').creative_work
            self.stdout.write(self.style.SUCCESS('Found the Graveyard @ "{}"'.format(graveyard.id)))

            OSF_PP_USER_IDS = list(ShareUser.objects.filter(source__long_title__in=self.OSF_PP).values_list('id', flat=True))
            AGGREGATOR_USER_IDS = ShareUser.objects.filter(source__long_title__in=self.AGGREGATORS).values_list('id', flat=True)

            pps = Preprint.objects.filter(
                sources__in=AGGREGATOR_USER_IDS,
                date_modified__gte='2017-07-30',
                id__in=Preprint.objects.filter(sources__in=OSF_PP_USER_IDS)
            )

            for work in pps:
                dupes = {}

                for agent in work.related_agents.filter(type='share.person'):
                    dupes.setdefault((agent.given_name, agent.family_name), []).append(agent)

                # Filter down to just duplicated agents
                for k in list(dupes.keys()):
                    if len(dupes[k]) < 2:
                        del dupes[k]

                # If there are no dupes, we have nothing todo
                if not dupes:
                    continue

                self.stdout.write('=== Processing Work "{}" Modified On {} ==='.format(work.id, work.date_modified))

                for agents in dupes.values():
                    # Order by # of identifiers and a preference towards OSF sources
                    core_agent = list(sorted(agents, key=lambda x: (agent.sources.filter(source__long_title__in=self.OSF_PP).exists(), x.identifiers.count()), reverse=True))[0]

                    self.stdout.write('\tSmashing {} into {} from {} identified by {}'.format(
                        [a for a in agents if a != core_agent],
                        core_agent,
                        core_agent.sources.values_list('source__long_title', flat=True),
                        core_agent.identifiers.values_list('uri', flat=True),
                    ))

                    for agent in agents:
                        if agent == core_agent:
                            continue
                        for identifier in agent.identifiers.all():
                            self.stdout.write('\t\tRepointing {}: {} -> {}'.format(identifier.uri, agent, core_agent))
                            if not options.get('dry'):
                                identifier.administrative_change(agent=core_agent)

                        for rel in agent.work_relations.all():
                            self.stdout.write('\t\tReassigning {}: {} -> {}'.format(rel, rel.creative_work.id, graveyard.id))
                            if not options.get('dry'):
                                rel.administrative_change(creative_work=graveyard, type=''.join(random.sample(string.ascii_letters, 5)))

                    self.stdout.write(self.style.SUCCESS('\tSuccessfully Processed Agent "{}"'.format(agent.id)))
                self.stdout.write('Bumping last_modified on work')
                if not options.get('dry'):
                    work.administrative_change(allow_empty=True)
                self.stdout.write(self.style.SUCCESS('Successfully Processed Work "{}"\n'.format(work.id)))

            if not options.get('commit'):
                raise ValueError('not_dry not set, rolling backing')
