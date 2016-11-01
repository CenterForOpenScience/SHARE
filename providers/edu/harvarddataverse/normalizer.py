from share.normalize import *


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix


class Contributor(Parser):
    agent = Delegate(Person, ctx)


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class CreativeWork(Parser):
    schema = 'Dataset'
    # TODO: get schema
    title = ctx.name
    description = Try(ctx.description)
    date_published = ParseDate(ctx.published_at)
    identifiers = Map(Delegate(WorkIdentifier), ctx.url)

    related_agents = Map(Delegate(Person), ctx.authors)

    class Extra:
        citation = ctx.citation
