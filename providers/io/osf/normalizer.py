from share.normalize import ctx
from share.normalize.parsers import Parser


class CreativeWork(Parser):
    title = ctx.attributes.title
    description = ctx.attributes.description
    contributors = ctx.contributors['*']
    institutions = ctx.embeds.affiliated_institutions.data['*']
    created = ctx.attributes.date_created
    subject = ctx.attributes.category
    tags = ctx.attributes.tags['*']


class Contributor(Parser):
    person = ctx
    order_cited = ctx['index']
    cited_name = ctx.embeds.users.data.attributes.full_name


class Tag(Parser):
    name = ctx


class Person(Parser):
    given_name = ctx.embeds.users.data.attributes.given_name
    family_name = ctx.embeds.users.data.attributes.family_name
    additional_name = ctx.embeds.users.data.attributes.middle_names
    suffix = ctx.embeds.users.data.attributes.suffix


class ThroughInstitutions(Parser):
    institution = ctx


class Institution(Parser):
    name = ctx.attributes.name
    url = ctx.relationships.links.related.href
