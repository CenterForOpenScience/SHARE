from share.normalize import *

from share.normalize import ctx
from share.normalize.parsers import Parser


class CreativeWork(Parser):
    title = ctx.attributes.title
    description = ctx.attributes.description
    contributors = ctx.contributors['*']
    institutions = ctx.contributors.institutions['*']
    created = ctx.attributes.date_created
    subject = ctx.attributes.category


class Contributor(Parser):
    person = ctx


class Person(Parser):
    given_name = ctx.contributor.embeds.users.data.attributes.given_name
    family_name = ctx.contributor.embeds.users.data.attributes.family_name
    additional_name = ctx.contributor.embeds.users.data.attributes.middle_names
    suffix = ctx.contributor.embeds.users.data.attributes.suffix


class Instutions(Parser):
    url = ctx.links.self.href