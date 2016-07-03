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

    class Extra:
        files = ctx.relationships.files.links.related.href
        parent = ctx.relationships.maybe('parent.links.related.href')
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
        node_license = ctx.attributes.node_license


class Contributor(Parser):
    person = ctx
    order_cited = ctx['index']
    cited_name = ctx.embeds.users.data.attributes.full_name


class ThroughTags(Parser):
    tag = ctx


class Tag(Parser):
    name = ctx
    type = ctx


class Taxonomy(Parser):
    name = ctx


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


class ThroughInstitutions(Parser):
    institution = ctx


class Institution(Parser):
    name = ctx.attributes.name
    url = ctx.links.self

    class Extra:
        nodes = ctx.relationships.nodes.links.related.href
        users = ctx.relationships.users.links.related.href
        registrations = ctx.relationships.registrations.links.related.href
        description = ctx.attributes.description
