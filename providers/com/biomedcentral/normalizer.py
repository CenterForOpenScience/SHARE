from share.normalize import *  # noqa


class CreativeWork(Parser):
    title = ctx.title
    contributors = ctx.creators('*')
    description = ctx.abstract
    date_published = ctx.publicationDate
    doi = ctx.doi
    # subject = ctx.genre


class Contributor(Parser):
    person = ctx
    cited_name = ctx.creator
    order_cited = ctx('index')


class Person(Parser):
    given_name = ParseName(ctx.creator).first
    family_name = ParseName(ctx.creator).last
    additional_name = ParseName(ctx.creator).middle
    suffix = ParseName(ctx.creator).suffix
