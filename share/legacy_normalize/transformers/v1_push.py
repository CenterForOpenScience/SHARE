import re

from share.legacy_normalize.transform.chain import links as tools
from share.legacy_normalize.transform.chain import ctx, ChainTransformer
from share.legacy_normalize.transform.chain.parsers import Parser

THE_REGEX = re.compile(r'(^the\s|\sthe\s)')


class WorkIdentifier(Parser):
    uri = ctx


class AgentIdentifier(Parser):
    uri = ctx


class IsAffiliatedWith(Parser):
    # Moved below Agent definition to resolve cyclical references
    # related = tools.Delegate(OrgAgent)
    pass


class Agent(Parser):
    schema = tools.GuessAgentType(ctx.name)

    name = ctx.name

    related_agents = tools.Map(
        tools.Delegate(IsAffiliatedWith),
        tools.Try(ctx.affiliation)
    )

    identifiers = tools.Map(
        tools.Delegate(AgentIdentifier),
        tools.Map(
            tools.IRI(),
            tools.Try(ctx.sameAs),
            tools.Try(ctx.email)
        )
    )

    class Extra:
        givenName = tools.Try(ctx.givenName)
        familyName = tools.Try(ctx.familyName)
        additonalName = tools.Try(ctx.additionalName)
        name = tools.Try(ctx.name)


class OrgAgent(Agent):
    schema = tools.GuessAgentType(ctx.name, default='organization')


IsAffiliatedWith.related = tools.Delegate(OrgAgent)


class Creator(Parser):
    agent = tools.Delegate(Agent, ctx)
    cited_as = ctx.name
    order_cited = ctx('index')


class Publisher(Parser):
    agent = tools.Delegate(OrgAgent, ctx)
    cited_as = ctx.name


class FundingAgent(Parser):
    schema = tools.GuessAgentType(ctx.sponsorName, default='organization')

    name = ctx.sponsorName

    identifiers = tools.Map(
        tools.Delegate(AgentIdentifier),
        tools.IRI(tools.Try(ctx.sponsorIdentifier))
    )


class Award(Parser):
    name = ctx.awardName
    uri = tools.IRI(tools.Try(ctx.awardIdentifier))


class ThroughAwards(Parser):
    award = tools.Delegate(Award, ctx)


class Funder(Parser):
    agent = tools.Delegate(FundingAgent, ctx.sponsor)
    cited_as = ctx.sponsor.sponsorName

    awards = tools.Map(
        tools.Delegate(ThroughAwards),
        tools.Try(ctx.award)
    )


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = tools.Delegate(Tag, ctx)


class Subject(Parser):
    name = ctx


class ThroughSubjects(Parser):
    subject = tools.Delegate(Subject, ctx)


class CreativeWork(Parser):
    title = ctx.title
    description = tools.Try(ctx.description)
    is_deleted = tools.RunPython('_is_deleted', tools.Try(ctx.otherProperties))
    date_updated = tools.ParseDate(tools.Try(ctx.providerUpdatedDateTime))
    rights = tools.Join(tools.Try(ctx.licenses.uri))

    # Note: this is only taking the first language in the case of multiple languages
    language = tools.ParseLanguage(
        tools.Try(ctx.languages[0]),
    )

    related_agents = tools.Concat(
        tools.Map(
            tools.Delegate(Creator),
            tools.Try(ctx.contributors)
        ),
        tools.Map(
            tools.Delegate(Publisher),
            tools.Try(ctx.publisher)
        ),
        tools.Map(
            tools.Delegate(Funder),
            tools.Try(ctx.sponsorships)
        )
    )

    identifiers = tools.Map(
        tools.Delegate(WorkIdentifier),
        tools.Map(
            tools.IRI(),
            tools.RunPython(
                'unique',
                tools.Concat(
                    tools.Try(ctx.uris.canonicalUri),
                    tools.Try(ctx.uris.providerUris),
                    tools.Try(ctx.uris.descriptorUris),
                    tools.Try(ctx.uris.objectUris)
                )
            )
        )
    )

    subjects = tools.Map(
        tools.Delegate(ThroughSubjects),
        tools.Subjects(
            tools.Try(ctx.subjects)
        )
    )

    tags = tools.Map(
        tools.Delegate(ThroughTags),
        tools.Try(ctx.tags),
        tools.Try(ctx.subjects)
    )

    class Extra:
        """
        Fields that are combined in the base parser are relisted as singular elements that match
        their original entry to preserve raw data structure.
        """
        freeToRead = tools.Try(ctx.freeToRead)
        languages = tools.Try(ctx.languages)
        licenses = tools.Try(ctx.licenses)
        otherProperties = tools.Try(ctx.otherProperties)
        publisher = tools.Try(ctx.publisher)
        subjects = tools.Try(ctx.subjects)
        sponsorships = tools.Try(ctx.sponsorships)
        tags = tools.Try(ctx.tags)
        uris = tools.Try(ctx.uris)
        version = tools.Try(ctx.version)

    def unique(self, items):
        return list(sorted(set(items)))

    def _is_deleted(self, properties):
        for prop in properties or []:
            if prop['name'] == 'status':
                return 'deleted' in prop['properties'].get('status', [])
        return False


class V1Transformer(ChainTransformer):
    VERSION = 1
    root_parser = CreativeWork
