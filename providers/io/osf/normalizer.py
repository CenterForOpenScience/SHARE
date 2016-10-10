import re

from share.normalize import ctx
from share.normalize.parsers import Parser
from share.normalize import tools


class EntityIdentifier(Parser):
    uri = ctx


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

    entityidentifiers = tools.Map(tools.Delegate(EntityIdentifier), ctx.embeds.users.data.links.html)

    class Extra:
        nodes = tools.Try(ctx.embeds.users.data.relationships.nodes.links.related.href)
        locale = tools.Try(ctx.embeds.users.data.attributes.locale)
        date_registered = tools.Try(ctx.embeds.users.data.attributes.date_registered)
        active = tools.Try(ctx.embeds.users.data.attributes.active)
        timezone = tools.Try(ctx.embeds.users.data.attributes.timezone)
        profile_image = tools.Try(ctx.embeds.users.data.links.profile_image)


class Contribution(Parser):
    order_cited = ctx.attributes.index
    bibliographic = ctx.attributes.bibliographic
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
    entityidentifiers = tools.Map(Delegate(EntityIdentifier), ctx.links.self)

    class Extra:
        nodes = ctx.relationships.nodes.links.related.href
        users = ctx.relationships.users.links.related.href
        registrations = ctx.relationships.registrations.links.related.href
        description = ctx.attributes.description


class CreativeWorkIdentifier(Parser):
    uri = ctx
    #uri = tools.IRILink(ctx)


class RelatedProject(Parser):
    # Don't save it as a Project, it could be a Preprint
    schema = 'CreativeWork'
    creativeworkidentifiers = tools.Map(tools.Delegate(CreativeWorkIdentifier), ctx)


class ParentWorkRelation(Parser):
    schema = 'WorkRelation'
    to_work = tools.Delegate(RelatedProject, ctx)
    relation_type = tools.Static('is_part_of')


class Project(Parser):
    title = ctx.attributes.title
    description = ctx.attributes.description
    contributors = tools.Map(Contribution.using(entity=tools.Delegate(Person), contribution_type=tolos.Static('cited_contributor')), ctx['contributors'])
    institutions = tools.Map(
        tools.Delegate(Contribution.using(entity=tools.Delegate(Institution), contribution_type=tools.Static('affiliation'))),
        ctx.embeds.affiliated_institutions.data
    )
    date_updated = tools.ParseDate(ctx.attributes.date_modified)
    tags = tools.Map(tools.Delegate(ThroughTags), ctx.attributes.category, ctx.attributes.tags)
    rights = tools.Maybe(ctx, 'attributes.node_license')
    creativeworkidentifiers = tools.Map(tools.Delegate(CreativeWorkIdentifier), ctx.links.html)
    related_works = tools.Map(
        tools.Delegate(ParentWorkRelation),
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
