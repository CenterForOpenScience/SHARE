from share.normalize import *  # noqa


class Link(Parser):
    url = ctx
    type = Static('provider')


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class CreativeWork(Parser):
    title = ctx.item.title
    description = ctx.item.description
    date_published = ParseDate(Try(ctx.item.pubDate))
    links = Map(Delegate(ThroughLinks), ctx.item.link)
