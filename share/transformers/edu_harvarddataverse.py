from share.transform.chain import *


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix


class Creator(Parser):
    agent = Delegate(Person, ctx)
    order_cited = ctx('index')
    cited_as = ctx


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class CreativeWork(Parser):
    schema = 'dataset'
    title = ctx.name
    description = Try(ctx.description)
    date_published = ParseDate(ctx.published_at)
    identifiers = Map(Delegate(WorkIdentifier), ctx.url)

    related_agents = Map(Delegate(Creator), Try(ctx.authors))

    class Extra:
        citation = ctx.citation


class HarvardTransformer(ChainTransformer):
    VERSION = 1
    root_parser = CreativeWork
