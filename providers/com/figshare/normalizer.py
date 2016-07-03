from share.normalize import *  # noqa


class Person(Parser):
    given_name = ParseName(ctx.author_name).first
    family_name = ParseName(ctx.author_name).last


class Contributor(Parser):
    order_cited = ctx('index')
    cited_name = ctx.author_name
    person = Delegate(Person, ctx)


class CreativeWork(Parser):
    # doi = ctx.DOI
    title = ctx.title
    description = ctx.description
    contributors = Map(Delegate(Contributor), ctx.authors)
