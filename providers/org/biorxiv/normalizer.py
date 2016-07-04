from share.normalize import links
from share.normalize.parsers import Parser

ctx = links.Context()


class Publisher(Parser):
    name = ctx


class Association(Parser):
    pass


class Person(Parser):
    given_name = links.ParseName(ctx).first
    family_name = links.ParseName(ctx).last
    additional_name = links.ParseName(ctx).middle
    suffix = links.ParseName(ctx).suffix


class Contributor(Parser):
    order_cited = ctx('index')
    person = links.Delegate(Person, ctx)
    cited_name = ctx


class CreativeWork(Parser):
    title = ctx.item['dc:title']
    description = ctx.item.description
    contributors = links.Map(links.Delegate(Contributor), ctx.item['dc:creator'])
    published = ctx.item['dc:date']
    publishers = links.Map(
        links.Delegate(Association.using(entity=links.Delegate(Publisher))),
        ctx.item['dc:publisher']
    )
    # doi = ctx.item['dc:identifier']
