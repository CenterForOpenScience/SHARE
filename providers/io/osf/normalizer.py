import re

from share.normalize import ctx
from share.normalize.parsers import Parser
from share.normalize import tools


class Identifier(Parser):
    url = ctx


class PersonIdentifier(Parser):
    identifier = tools.Delegate(Identifier, ctx)


class Person(Parser):
    given_name = tools.OneOf(
        ctx.embeds.users.data.attributes.given_name,
        ctx.embeds.users.errors[0].meta.given_name,
    )
    family_name = tools.OneOf(
        ctx.embeds.users.data.attributes.family_name,
        ctx.embeds.users.errors[0].meta.family_name,
    )
    additional_name = tools.OneOf(
        ctx.embeds.users.data.attributes.middle_names,
        ctx.embeds.users.errors[0].meta.middle_names,
    )
    suffix = tools.OneOf(
        ctx.embeds.users.data.attributes.suffix,
        ctx.embeds.users.errors[0].meta.suffix,
    )

    identifiers = tools.Map(tools.Delegate(PersonIdentifier), ctx.embeds.users.data.links.html)

    class Extra:
        nodes = tools.Try(ctx.embeds.users.data.relationships.nodes.links.related.href)
        locale = tools.Try(ctx.embeds.users.data.attributes.locale)
        date_registered = tools.Try(ctx.embeds.users.data.attributes.date_registered)
        active = tools.Try(ctx.embeds.users.data.attributes.active)
        timezone = tools.Try(ctx.embeds.users.data.attributes.timezone)
        profile_image = tools.Try(ctx.embeds.users.data.links.profile_image)


class Contributor(Parser):
    person = tools.Delegate(Person, ctx)
    order_cited = ctx('index')
    cited_name = tools.OneOf(
        ctx.embeds.users.data.attributes.full_name,
        ctx.embeds.users.errors[0].meta.full_name,
    )


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


class WorkIdentifier(Parser):
    identifier = tools.Delegate(Identifier, ctx)


class RelatedProject(Parser):
    # Don't save it as a Project, it could be a Preprint
    schema = 'CreativeWork'
    identifiers = tools.Map(tools.Delegate(WorkIdentifier), ctx)


class ParentRelation(Parser):
    schema = 'Relation'
    to_work = tools.Delegate(RelatedProject, ctx)
    relation_type = tools.Static('is_part_of')


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
    identifiers = tools.Map(tools.Delegate(WorkIdentifier), ctx.links.html)
    related_works = tools.Map(
        tools.Delegate(ParentRelation),
        tools.RunPython('api_url_to_guid', tools.Try(ctx.relationships.parent.links.related.href))
    )

    def api_url_to_guid(self, url):
        # If only there were relationships.parent.links.related.html in addition to href
        match = re.fullmatch(r'https://api.osf.io/v2/nodes/(\w+)/', url)
        if match:
            guid = match.group(1)
            return 'https://osf.io/{}/'.format(guid)
        return None

    class Extra:
        date_created = tools.ParseDate(ctx.attributes.date_created)
        files = ctx.relationships.files.links.related.href
        parent = tools.Try(ctx.relationships.parent.links.related.href)
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
