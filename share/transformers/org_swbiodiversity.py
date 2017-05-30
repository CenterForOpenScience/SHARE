from share.transform.chain import ctx, ChainTransformer
from share.transform.chain import links as tools
from share.transform.chain.parsers import Parser


class AgentIdentifier(Parser):
    uri = tools.IRI(ctx)


class WorkIdentifier(Parser):
    uri = tools.IRI(ctx)


class Organization(Parser):
    name = ctx


class Publisher(Parser):
    agent = tools.Delegate(Organization, ctx)


class Institution(Parser):
    name = ctx


class IsAffiliatedWith(Parser):
    related = tools.Delegate(Institution)


class Person(Parser):
    name = tools.Try(ctx.name)
    identifiers = tools.Map(tools.Delegate(AgentIdentifier), tools.Try(ctx.email))


class Creator(Parser):
    agent = tools.Delegate(Person, ctx)


class Dataset(Parser):
    title = tools.Try(ctx['title'])
    description = tools.Try(ctx['description'])

    #
    related_agents = tools.Map(tools.Delegate(Creator), tools.Try(ctx.contact))

    # related_works

    class Extra:
        identifiers = tools.Try(ctx['identifier'])
        access_rights = tools.Try(ctx['access-rights'])
        usage_rights = tools.Try(ctx['usage-rights'])
        collection_statistics = tools.Try(ctx['collection-statistics'])


class SWTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Dataset
