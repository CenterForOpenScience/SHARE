from share.normalize import ctx
from share.normalize.parsers import Parser
from share.normalize.links import Delegate, Map, Maybe, Concat


class Person(Parser):
    given_name = ctx.piFirstName
    family_name = ctx.piLastName


class Contributor(Parser):
    person = Delegate(Person, ctx)
    order_cited = ctx('index')
    cited_name = ctx


class Institution(Parser):
    name = ctx
    # TODO - fix the URL with a custum callable and an ID
    url = ctx


class ThroughInstitutions(Parser):
    institution = Delegate(ctx, Institution)


class Award(Parser):
    description = ctx.fundsObligatedAmt
    # TODO - add a url and custom callable

    class Extra:
        awardee_city = ctx.awardeeCity


class ThroughAwards(Parser):
    award = Delegate(Award, ctx)


class Venue(Parser):
    name = Concat(ctx.awardeeCity, ctx.awardeeStateCode)


class ThroughVenues(Parser)
    venue = Delegate(Venue, ctx)


class CreativeWork(Parser):
    title = ctx.title
    contributors = Map(Delegate(Contributor), Concat(ctx.piFirstName, ctx.piLastName))

    awards = Delegate(ThroughAwards, ctx)
    venue = Delegate(ThroughVenues, ctx)

    institutions = Map(Delegate(ThroughInstitutions), ctx.agency)
    created = ctx.date

    class Extra:
        public_access_mandate = ctx.publicAccessMandate
