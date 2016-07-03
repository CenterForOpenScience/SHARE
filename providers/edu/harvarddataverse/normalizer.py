from share.normalize import *


class CreativeWork(Parser):
    title = ctx.name
    description = ctx.description
    published = ctx.published_at
    contributors = ctx.authors


class Contributor(Parser):
    person = ctx
    cited_name = ctx
    order_cited = ctx['index']


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix
