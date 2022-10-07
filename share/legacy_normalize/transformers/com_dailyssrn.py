from share.legacy_normalize.transform.chain import *  # noqa


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class CreativeWork(Parser):
    title = ctx.item.title
    description = ctx.item.description
    date_published = ParseDate(Try(ctx.item.pubDate))
    identifiers = Map(Delegate(WorkIdentifier), ctx.item.link)


class DailySSRNTransformer(ChainTransformer):
    VERSION = 1
    root_parser = CreativeWork
