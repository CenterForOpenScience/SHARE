from share.transform.chain import ctx, ChainTransformer, Maybe
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
    given_name = Maybe(ctx, 'first_name')
    family_name = Maybe(ctx, 'last_name')
    additional_name = Maybe(ctx, 'middle_name')
    identifiers = tools.Map(tools.Delegate(AgentIdentifier), tools.Try(ctx.email))


class Creator(Parser):
    agent = tools.Delegate(Person, ctx)


class Dataset(Parser):
    title = tools.Try(ctx['title'])
    description = tools.Try(ctx['description'])
    rights = tools.Try(ctx['usage-rights'])

    #
    related_agents = tools.Map(tools.Delegate(Creator), tools.RunPython('get_contributors', ctx))

    # related_works

    class Extra:
        identifiers = tools.Try(ctx['identifier'])
        access_rights = ctx['access-rights']
        collection_statistics = ctx['collection-statistics']

    def get_contributors(self, link):
        author = link['contact']['name']
        email = link['contact']['email']

        contribs = [{
            'author': author,
            'email': email
        }]

        return contribs


class SWTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Dataset
