from share.normalize import ctx
from share.normalize.parsers import Parser
from share.normalize.links import Delegate, Map, Maybe


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
    person = Delegate(Person, ctx)
    order_cited = ctx('index')
    cited_name = ctx.embeds.users.data.attributes.full_name


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


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
    type = 'provider'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Project(Parser):
    title = ctx.attributes.title
    description = ctx.attributes.description
    contributors = Map(Delegate(Contributor), ctx['contributors'])
    institutions = Map(
        Delegate(Association.using(entity=Delegate(Institution))),
        ctx.embeds.affiliated_institutions.data
    )
    created = ctx.attributes.date_created
    subject = Delegate(Tag, ctx.attributes.category)
    tags = Map(Delegate(ThroughTags), ctx.attributes.tags)
    rights = Maybe(ctx, 'attributes.node_license')
    links = Map(Delegate(ThroughLinks), ctx.links.html)

    class Extra:
        files = ctx.relationships.files.links.related.href
        parent = Maybe(ctx, 'relationships.parent.links.related.href')
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
