from share.normalize import *  # noqa


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix


class Contributor(Parser):
    order_cited = ctx['index']
    person = ctx
    cited_name = ctx


class CreativeWork(Parser):
    title = ctx.item('dc:title')
    description = ctx.item.description
    contributors = ctx.item('dc:creator')['*']
    published = ctx.item('dc:date')
    doi = ctx.item('dc:identifier')
