from share.normalize import *  # noqa


class Person(AbstractPerson):
    given_name = ParseName(ctx.author_name).first
    family_name = ParseName(ctx.author_name).last


class Contributor(AbstractContributor):
    person = ctx


class Manuscript(AbstractManuscript):
    title = ctx.title
    description = ctx.description
    # publish_date = ParseDate(ctx.published_date)
    contributors = ctx.authors['*']
