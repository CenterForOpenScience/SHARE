import arrow

import dateparser

from share.normalize import *


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix


class Contributor(Parser):
    person = Delegate(Person, ctx)
    cited_name = ctx
    order_cited = ctx('index')


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        if 'dataverse.harvard.edu' in link:
            return 'misc'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class CreativeWork(Parser):
    title = ctx.name
    description = ctx.description
    contributors = Map(Delegate(Contributor), ctx.authors)
    published = RunPython('parse_date', ctx.published_at)
    links = Concat(
        Delegate(ThroughLinks, ctx.url),
        Delegate(ThroughLinks, ctx.image_url),
    )

    def parse_date(self, date_str):
        return arrow.get(dateparser.parse(date_str)).to('UTC').isoformat()
