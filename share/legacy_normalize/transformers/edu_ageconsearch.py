import re

from share.legacy_normalize.transform.chain import *


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class AgentIdentifier(Parser):
    uri = ctx


class Agent(Parser):
    schema = GuessAgentType(ctx.name)
    name = ctx.name
    identifiers = Map(Delegate(AgentIdentifier), Try(IRI(ctx.email)))


class ContributorRelation(Parser):
    schema = 'Contributor'

    agent = Delegate(Agent, ctx)
    cited_as = ctx.name


class CreatorRelation(ContributorRelation):
    schema = 'Creator'

    order_cited = ctx('index')


class AffiliatedAgent(Parser):
    schema = GuessAgentType(ctx, default='organization')
    name = ctx


class AgentWorkRelation(Parser):
    agent = Delegate(AffiliatedAgent, ctx)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Subject(Parser):
    name = ctx


class ThroughSubjects(Parser):
    subject = Delegate(Subject, ctx)


class Preprint(Parser):
    title = Try(ctx.title)
    description = Try(ctx.abstract)
    identifiers = Concat(
        Map(Delegate(WorkIdentifier), ctx.primary_identifier),
        Map(Delegate(WorkIdentifier), ctx.uri),
        Map(Delegate(WorkIdentifier), Try(ctx.identifiers)),
    )

    related_agents = Concat(
        Map(
            Delegate(CreatorRelation),
            RunPython('get_agent_emails', ctx, 'authors', 'authors_email')
        ),
        Map(
            Delegate(ContributorRelation),
            RunPython('get_agent_emails', ctx, 'editors', 'editors_email')
        ),
        Map(
            Delegate(AgentWorkRelation),
            RunPython('get_affiliated_organization', Try(ctx.institution_association))
        )
    )

    tags = Map(Delegate(ThroughTags), Try(ctx.keywords))
    date_published = ParseDate(Try(ctx.issue_date))
    subjects = Map(Delegate(ThroughSubjects), Subjects(Try(ctx.jel_codes)))

    class Extra:
        other_titles = Try(ctx.other_titles)
        notes = Try(ctx.notes)
        editors = Try(ctx.editors)
        editors_email = Try(ctx.editors_email)
        authors = Try(ctx.authors)
        authors_email = Try(ctx.authors_email)
        series_report_number = Try(ctx.series_report_number)
        institution_association = Try(ctx.institution_association)
        collections = Try(ctx.collections)
        total_pages = Try(ctx.total_pages)
        from_page = Try(ctx.from_page)
        to_page = Try(ctx.to_page)
        identifiers = Try(ctx.identifiers)
        uri = ctx.uri

    def get_agent_emails(self, ctx, agent_key, email_key):
        """
            emails format: [name (email), name (email)]
        """
        try:
            agents = ctx[agent_key] if isinstance(ctx[agent_key], list) else [ctx[agent_key]]
        except KeyError:
            agents = []

        try:
            emails = ctx[email_key] if isinstance(ctx[email_key], list) else [ctx[email_key]]
        except KeyError:
            emails = []

        agent_objects = []

        for agent in agents:
            agent_object = {'name': agent}

            agent_email = next((x for x in emails if agent in x), None)

            if agent_email:
                agent_object['email'] = re.compile(r'\((\S+?)\)').search(agent_email).group(1)
            agent_objects.append(agent_object)

        return agent_objects

    def get_affiliated_organization(self, affiliation):
        """
            affiliation format: 'name>volume issue etc'
        """
        return affiliation.split('>')[0]


class AgeconTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Preprint
