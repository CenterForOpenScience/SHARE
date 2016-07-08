from share.normalize import ctx
from share.normalize import tools
from share.normalize.parsers import Parser
from share.normalize.utils import format_doi_as_url


class Publisher(Parser):
    name = ctx


class Association(Parser):
    pass


class Link(Parser):
    url = tools.RunPython('format_doi', ctx)
    # identifier will always be DOI
    type = tools.Static('doi')

    def format_doi(self, doi):
        return format_doi_as_url(self, doi)


class ThroughLinks(Parser):
    link = tools.Delegate(Link, ctx)


class Person(Parser):
    given_name = tools.ParseName(ctx).first
    family_name = tools.ParseName(ctx).last
    additional_name = tools.ParseName(ctx).middle
    suffix = tools.ParseName(ctx).suffix


class Contributor(Parser):
    order_cited = ctx('index')
    person = tools.Delegate(Person, ctx)
    cited_name = ctx


class Preprint(Parser):
    title = ctx.item['dc:title']
    description = ctx.item.description
    contributors = tools.Map(tools.Delegate(Contributor), ctx.item['dc:creator'])
    date_published = ctx.item['dc:date']
    publishers = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Publisher))),
        ctx.item['dc:publisher']
    )
    links = tools.Map(tools.Delegate(ThroughLinks), ctx.item['dc:identifier'])
