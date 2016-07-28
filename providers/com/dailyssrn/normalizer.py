import arrow

import dateparser

from share.normalize import *  # noqa


class Link(Parser):
    url = ctx
    type = Static('provider')


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class CreativeWork(Parser):
    title = ctx.item.title
    description = ctx.item.description
    date_published = RunPython('parse_date', ctx.item.pubDate)
    links = Map(Delegate(ThroughLinks), ctx.item.link)

    def parse_date(self, date_str):
        return arrow.get(dateparser.parse(date_str)).to('UTC').isoformat()
