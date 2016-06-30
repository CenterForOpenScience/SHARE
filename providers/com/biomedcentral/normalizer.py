from share.normalize import *

class CreativeWork(Parser):
    title = ctx.title
    contributors = ctx.creators['*']
    description = ctx.abstract
    published = ctx.publicationDate
    doi = ctx.doi
    # subject = ctx.genre


class Contributor(Parser):
    person = ctx


class Person(Parser):
    given_name = ParseName(ctx.creator).first
    family_name = ParseName(ctx.creator).last
    additional_name = ParseName(ctx.creator).middle
    suffix = ParseName(ctx.creator).suffix
