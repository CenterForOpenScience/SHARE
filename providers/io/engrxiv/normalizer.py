import furl

from share.normalize import ctx
from share.normalize import tools
from share.normalize.parsers import Parser


class Identifier(Parser):
    url = ctx
    base_url = tools.RunPython('get_base_url', ctx)

    def get_base_url(self, url):
        url = furl.furl(url)
        return '{}://{}'.format(url.scheme, url.host)


class ThroughIdentifiers(Parser):
    identifier = tools.Delegate(Identifier, ctx)


class Person(Parser):
    given_name = ctx.embeds.users.data.attributes.given_name
    family_name = ctx.embeds.users.data.attributes.family_name
    additional_name = ctx.embeds.users.data.attributes.middle_names
    suffix = ctx.embeds.users.data.attributes.suffix
    identifiers = tools.Map(
        tools.Delegate(ThroughIdentifiers),
        tools.Try(ctx.embeds.users.data.links.html),
        tools.Try(ctx.embeds.users.data.links.profile_image),
        tools.Try(ctx.embeds.users.errors[0].meta.profile_image)
    )

    class Extra:
        locale = ctx.embeds.users.data.attributes.locale
        date_registered = ctx.embeds.users.data.attributes.date_registered
        active = ctx.embeds.users.data.attributes.active
        timezone = ctx.embeds.users.data.attributes.timezone
        profile_image = ctx.embeds.users.data.links.profile_image


class Contributor(Parser):
    person = tools.Delegate(Person, ctx)
    order_cited = ctx.attributes.index
    bibliographic = ctx.attributes.bibliographic
    cited_name = ctx.embeds.users.data.attributes.full_name


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = tools.Delegate(Tag, ctx)


class Institution(Parser):
    name = ctx.attributes.name
    url = ctx.links.self

    class Extra:
        nodes = ctx.relationships.nodes.links.related.href
        users = ctx.relationships.users.links.related.href
        registrations = ctx.relationships.registrations.links.related.href
        description = ctx.attributes.description


class Association(Parser):
    pass


class Link(Parser):
    url = ctx
    type = tools.Static('provider')


class ThroughLinks(Parser):
    link = tools.Delegate(Link, ctx)


class Subject(Parser):
    name = ctx


class ThroughSubjects(Parser):
    subject = tools.Delegate(Subject, ctx)


class Preprint(Parser):

    title = ctx.attributes.title
    description = ctx.attributes.description
    contributors = tools.Map(tools.Delegate(Contributor), ctx.contributors)
    institutions = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Institution))),
        ctx.embeds.affiliated_institutions.data
    )
    # rights = tools.Try(ctx.attributes.node_license)
    date_updated = tools.ParseDate(ctx.attributes.date_modified)
    links = tools.Map(tools.Delegate(ThroughLinks), ctx.links.html)
    tags = tools.Map(tools.Delegate(ThroughTags), ctx.attributes.category, ctx.attributes.tags)
    subjects = tools.Map(tools.Delegate(ThroughSubjects), tools.Static('Engineering and technology'))

    class Extra:
        date_created = tools.ParseDate(ctx.attributes.date_created)
        date_modified = ctx.attributes.date_modified
