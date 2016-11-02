from share.normalize import ctx
from share.normalize import tools
from share.normalize.parsers import Parser


def format_url(award_id):
    return 'https://www.nsf.gov/awardsearch/showAward?AWD_ID={}'.format(award_id)


class WorkIdentifier(Parser):
    uri = tools.RunPython(format_url, ctx.id)


class FunderAgent(Parser):
    schema = tools.GuessAgentType(
        ctx.agency,
        default='organization'
    )

    name = ctx.agency


class Award(Parser):
    name = ctx.title
    description = ctx.fundsObligatedAmt
    uri = tools.RunPython(format_url, ctx.id)

    class Extra:
        funds_obligated_amt = ctx.fundsObligatedAmt
        award_id = ctx.id
        awardee_name = ctx.awardeeName
        awardee_city = ctx.awardeeCity
        awardee_state_code = tools.Try(ctx.awardeeStateCode)
        date = ctx.date


class ThroughAwards(Parser):
    award = tools.Delegate(Award, ctx)


class FunderRelation(Parser):
    schema = 'Funder'

    agent = tools.Delegate(FunderAgent, ctx)
    awards = tools.Map(tools.Delegate(ThroughAwards), ctx)


class AffiliatedAgent(Parser):
    schema = tools.GuessAgentType(
        ctx.awardeeName,
        default='organization'
    )

    name = ctx.awardeeName
    location = tools.Join(tools.Concat(ctx.awardeeCity, tools.Try(ctx.awardeeStateCode)), joiner=', ')

    class Extra:
        awardee_city = ctx.awardeeCity
        awardee_state_code = tools.Try(ctx.awardeeStateCode)


class IsAffiliatedWith(Parser):
    related = tools.Delegate(AffiliatedAgent, ctx)


class ContributorAgent(Parser):
    schema = 'Person'

    family_name = ctx.piLastName
    given_name = ctx.piFirstName

    related_agents = tools.Map(tools.Delegate(IsAffiliatedWith), ctx)


class ContributorRelation(Parser):
    schema = 'Contributor'

    agent = tools.Delegate(ContributorAgent, ctx)
    cited_as = tools.Join(tools.Concat(ctx.piFirstName, ctx.piLastName), joiner=' ')


class CreativeWork(Parser):
    title = ctx.title

    identifiers = tools.Map(tools.Delegate(WorkIdentifier), ctx)

    related_agents = tools.Concat(
        tools.Map(tools.Delegate(FunderRelation), ctx),
        tools.Map(tools.Delegate(ContributorRelation), ctx)
    )

    date_updated = tools.ParseDate(ctx.date)

    class Extra:
        public_access_mandate = ctx.publicAccessMandate
