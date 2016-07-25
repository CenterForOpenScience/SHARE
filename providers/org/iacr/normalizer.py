from share.normalize import *
from share.normalize import links
from share.normalize.utils import format_doi_as_url


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        if 'eprint.iacr.org' in link:
            return 'provider'
        return 'misc'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Publisher(Parser):
    name = ctx


class Funder(Parser):
    name = ctx.name


class Award(Parser):
    award = ctx.award


class Association(Parser):
    pass


class Organization(Parser):
    name = Maybe(ctx, 'name')


class Affiliation(Parser):
    pass


class Identifier(Parser):
    base_url = 'https://orcid.org'
    url = ctx


class ThroughIdentifiers(Parser):
    identifier = Delegate(Identifier, ctx)


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix


class Contributor(Parser):
    person = Delegate(Person, ctx)
    order_cited = ctx('index')
    cited_name = ctx


class Tag(Parser):
    name = ctx


class CreativeWork(Parser):
    """
    Documentation for CrossRef's metadata can be found here:
    https://github.com/CrossRef/rest-api-doc/blob/master/api_format.md
    """
    print(ctx)
    def format_doi_as_url(self, doi):
        return format_doi_as_url(self, doi)

    title = Maybe(ctx, 'title')
    description = Maybe(ctx, 'description')

    contributors = Map(
        Delegate(Contributor),
        Concat(Maybe(ctx, 'authors'))
    )
    links = Map(Delegate(ThroughLinks), ctx.link)
