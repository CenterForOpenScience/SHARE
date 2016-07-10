from share.normalize import *
from share.normalize import links


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        if 'id.crossref.org' in link:
            return 'provider'
        return 'misc'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Publisher(Parser):
    name = ctx


class Association(Parser):
    pass


class Organization(Parser):
    name = Maybe(ctx, 'name')


class Affiliation(Parser):
    pass


class Person(Parser):
    given_name = ctx.given
    family_name = ctx.family
    affiliations = Map(Delegate(Affiliation.using(entity=Delegate(Organization))), Maybe(ctx, 'affiliation'))


class Contributor(Parser):
    person = Delegate(Person, ctx)
    order_cited = ctx('index')
    cited_name = links.Join(Concat(ctx.given, ctx.family), ' ')


class CreativeWork(Parser):
    # Dates in CrossRef metadata are often incomplete, see: https://github.com/CrossRef/rest-api-doc/blob/master/rest_api.md#notes-on-dates
    title = Join(ctx.title)
    description = Join(Maybe(ctx, 'subtitle'))
    contributors = Map(Delegate(Contributor), Maybe(ctx, 'author'))
    links = Map(Delegate(ThroughLinks), Maybe(ctx, 'URL'))
    publishers = Map(Delegate(Association.using(entity=Delegate(Publisher))), Maybe(ctx, 'publisher'))
