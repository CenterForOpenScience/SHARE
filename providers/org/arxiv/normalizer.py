from share.normalize import *  # noqa


class Person(Parser):
    given_name = ParseName(ctx.name[0].text()).first
    family_name = ParseName(ctx.name[0].text()).last
    additional_name = ParseName(ctx.name[0].text()).middle
    suffix = ParseName(ctx.name[0].text()).suffix


class Contributor(Parser):
    person = ctx


class CreativeWork(Parser):
    title = ctx.title[0].text()
    description = ctx.summary[0].text()
    contributors = ctx.author['*']
