from share.normalize import *


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix


class Contributor(Parser):
    person = Delegate(Person, ctx)
    cited_name = ctx
    order_cited = ctx('index')


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        elif 'dataverse.harvard.edu' in link:
            return 'provider'
        return 'misc'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class CreativeWork(Parser):
    title = ctx.name
    description = Try(ctx.description)
    contributors = Map(Delegate(Contributor), Try(ctx.authors))
    date_published = ParseDate(ctx.published_at)
    links = Concat(
        Delegate(ThroughLinks, ctx.url),
        Delegate(ThroughLinks, ctx.image_url),
    )
