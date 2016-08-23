from share.normalize import ctx
from share.normalize.parsers import Parser
from share.normalize import tools


class Person(Parser):
    given_name = ctx.embeds.users.data.attributes.given_name
    family_name = ctx.embeds.users.data.attributes.family_name
    additional_name = ctx.embeds.users.data.attributes.middle_names
    suffix = ctx.embeds.users.data.attributes.suffix
    url = ctx.embeds.users.data.links.html

    class Extra:
        nodes = ctx.embeds.users.data.relationships.nodes.links.related.href
        locale = ctx.embeds.users.data.attributes.locale
        date_registered = ctx.embeds.users.data.attributes.date_registered
        active = ctx.embeds.users.data.attributes.active
        timezone = ctx.embeds.users.data.attributes.timezone
        profile_image = ctx.embeds.users.data.links.profile_image


class Contributor(Parser):
    person = tools.Delegate(Person, ctx)
    order_cited = ctx('index')
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


class Project(Parser):
    title = ctx.attributes.title
    description = ctx.attributes.description
    contributors = tools.Map(tools.Delegate(Contributor), ctx['contributors'])
    institutions = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Institution))),
        ctx.embeds.affiliated_institutions.data
    )
    date_updated = tools.ParseDate(ctx.attributes.date_modified)
    tags = tools.Map(tools.Delegate(ThroughTags), ctx.attributes.category, ctx.attributes.tags)
    rights = tools.Maybe(ctx, 'attributes.node_license')
    links = tools.Map(tools.Delegate(ThroughLinks), ctx.links.html)

    class Extra:
        date_created = tools.ParseDate(ctx.attributes.date_created)
        files = ctx.relationships.files.links.related.href
        parent = tools.Maybe(ctx, 'relationships.parent.links.related.href')
        forks = ctx.relationships.forks.links.related.href
        root = ctx.relationships.root.links.related.href
        comments = ctx.relationships.comments.links.related.href
        registrations = ctx.relationships.registrations.links.related.href
        logs = ctx.relationships.logs.links.related.href
        node_links = ctx.relationships.node_links.links.related.href
        wikis = ctx.relationships.wikis.links.related.href
        children = ctx.relationships.children.links.related.href
        fork = ctx.attributes.fork
        date_modified = ctx.attributes.date_modified
        collection = ctx.attributes.collection
        registration = ctx.attributes.registration
        type = ctx.type
        id = ctx.id
