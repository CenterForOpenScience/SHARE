from share.normalize import ctx, links
from share.normalize.parsers import Parser
from share.normalize.utils import format_doi_as_url


class Publisher(Parser):
    name = ctx


class Association(Parser):
    pass


class Link(Parser):
    url = links.RunPython('format_doi', ctx)
    # identifier will always be DOI
    type = 'doi'

    def format_doi(self, doi):
        return format_doi_as_url(self, doi)


class ThroughLinks(Parser):
    link = links.Delegate(Link, ctx)


class Person(Parser):
    given_name = links.ParseName(ctx).first
    family_name = links.ParseName(ctx).last
    additional_name = links.ParseName(ctx).middle
    suffix = links.ParseName(ctx).suffix


class Contributor(Parser):
    order_cited = ctx('index')
    person = links.Delegate(Person, ctx)
    cited_name = ctx


class Preprint(Parser):
    title = ctx.item['dc:title']
    description = ctx.item.description
    contributors = links.Map(links.Delegate(Contributor), ctx.item['dc:creator'])
    published = ctx.item['dc:date']
    publishers = links.Map(
        links.Delegate(Association.using(entity=links.Delegate(Publisher))),
        ctx.item['dc:publisher']
    )
    links = links.Map(links.Delegate(ThroughLinks), ctx.item['dc:identifier'])
