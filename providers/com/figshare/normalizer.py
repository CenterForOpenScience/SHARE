import arrow

import dateparser

from share.normalize import *  # noqa


class Person(Parser):
    given_name = ParseName(ctx.author_name).first
    family_name = ParseName(ctx.author_name).last


class Contributor(Parser):
    order_cited = ctx('index')
    cited_name = ctx.author_name
    person = Delegate(Person, ctx)


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        if 'figshare.com' in link:
            return 'provider'
        return 'misc'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class CreativeWork(Parser):
    title = ctx.title
    description = ctx.description
    contributors = Map(Delegate(Contributor), ctx.authors)
    date_published = RunPython('parse_date', ctx.published_date)
    links = Map(Delegate(ThroughLinks), ctx.url, ctx.DOI, ctx.links)

    class Extra:
        modified = RunPython('parse_date', ctx.modified_date)

    def parse_date(self, date_str):
        return arrow.get(dateparser.parse(date_str)).to('UTC').isoformat()
