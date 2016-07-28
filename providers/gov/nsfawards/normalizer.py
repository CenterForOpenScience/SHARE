from share.normalize import ctx
from share.normalize import tools
from share.normalize.parsers import Parser


class Person(Parser):
    given_name = ctx.piFirstName
    family_name = ctx.piLastName


class Contributor(Parser):
    person = tools.Delegate(Person, ctx)
    order_cited = ctx('index')
    cited_name = tools.Join(tools.Concat(ctx.piFirstName, ctx.piLastName), joiner=' ')


class Institution(Parser):
    name = ctx.agency


class Association(Parser):
    pass


class Award(Parser):
    description = ctx.fundsObligatedAmt
    url = tools.RunPython('format_url', ctx)

    def format_url(self, ctx):
        return 'https://www.nsf.gov/awardsearch/showAward?AWD_ID={}'.format(ctx['id'])

    class Extra:
        awardee_city = ctx.awardeeCity
        funds_obligated_amt = ctx.fundsObligatedAmt
        name = tools.Try(ctx.awardeeName)
        awardee_city = ctx.awardeeCity
        awardee_state_code = tools.Try(ctx.awardeeStateCode)


class ThroughAwards(Parser):
    award = tools.Delegate(Award, ctx)


class Venue(Parser):
    name = tools.Try(ctx.awardeeName)
    location = tools.Join(tools.Concat(ctx.awardeeCity, tools.Try(ctx.awardeeStateCode)), joiner=', ')

    class Extra:
        awardee_city = ctx.awardeeCity
        awardee_state_code = tools.Try(ctx.awardeeStateCode)


class ThroughVenues(Parser):
    venue = tools.Delegate(Venue, ctx)


class Link(Parser):
    url = tools.RunPython('format_url', ctx)
    type = 'provider'

    def format_url(self, ctx):
        return 'https://www.nsf.gov/awardsearch/showAward?AWD_ID={}'.format(ctx['id'])


class ThroughLinks(Parser):
    link = tools.Delegate(Link, ctx)


class CreativeWork(Parser):
    title = ctx.title
    contributors = tools.Map(tools.Delegate(Contributor), ctx)
    links = tools.Map(tools.Delegate(ThroughLinks), ctx)

    awards = tools.Map(tools.Delegate(ThroughAwards), ctx)
    venues = tools.Map(tools.Delegate(ThroughVenues), ctx)
    institutions = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Institution))), ctx
    )

    date_created = tools.ParseDate(ctx.date)

    class Extra:
        public_access_mandate = ctx.publicAccessMandate
