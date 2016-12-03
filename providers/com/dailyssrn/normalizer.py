from share.normalize import *  # noqa


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class CreativeWork(Parser):
    title = ctx.item.title
    description = ctx.item.description
    date_published = ParseDate(Try(ctx.item.pubDate))
    identifiers = Map(Delegate(WorkIdentifier), ctx.item.link)
