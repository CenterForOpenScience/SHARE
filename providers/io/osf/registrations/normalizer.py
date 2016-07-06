from share.normalize import ctx
from share.normalize.parsers import Parser
from share.normalize.links import Delegate, Map, Maybe, Concat, RunPython


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
    name = Maybe(ctx, 'attributes.name')
    url = ctx.links.self

    class Extra:
        nodes = ctx.relationships.nodes.links.related.href
        users = ctx.relationships.users.links.related.href
        registrations = ctx.relationships.registrations.links.related.href
        description = ctx.attributes.description


class ThroughInstitutions(Parser):
    institution = Delegate(Institution, ctx)


class Link(Parser):
    url = RunPython('parse_url', ctx)
    type = RunPython('parse_type', ctx)

    def parse_url(self, ctx):
        if isinstance(ctx, str):
            return ctx
        else:
            return_id = ctx['attributes']['value']
            if ctx['attributes']['category'] == 'doi':
                return 'http://dx/doi.org/{}'.format(return_id)
            else:
                return 'http://whatisthis/{}'.format(return_id)


    def parse_type(self, ctx):
        if isinstance(ctx, str):
            return 'provider'
        else:
            return ctx['attributes']['category']


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Registration(Parser):
    title = ctx.attributes.title
    description = ctx.attributes.description
    contributors = Map(Delegate(Contributor), ctx['contributors'])
    institutions = Map(
        Delegate(ThroughInstitutions),
        ctx.embeds.affiliated_institutions.data
    )
    created = ctx.attributes.date_created
    subject = Delegate(Tag, ctx.attributes.category)
    tags = Map(Delegate(ThroughTags), ctx.attributes.tags)
    rights = Maybe(ctx, 'attributes.node_license')
    free_to_read_date = Maybe(ctx.attributes, 'embargo_end_date')
    links = Concat(
        Delegate(ThroughLinks, ctx.links.html),
        Map(Delegate(ThroughLinks), ctx.embeds.identifiers.data)
    )


    class Extra:
        files = ctx.relationships.files.links.related.href
        registration_schema = ctx.relationships.registration_schema.links.related.href
        logs = ctx.relationships.logs.links.related.href
        forks = ctx.relationships.forks.links.related.href
        root = ctx.relationships.root.links.related.href
        comments = ctx.relationships.comments.links.related.href
        registered_from = ctx.relationships.registered_from.links.related.href
        node_links = ctx.relationships.node_links.links.related.href
        wikis = ctx.relationships.wikis.links.related.href
        children = ctx.relationships.children.links.related.href

        fork = ctx.attributes.fork
        pending_registration_approval = ctx.attributes.pending_registration_approval
        date_modified = ctx.attributes.date_modified
        registration_supplement = ctx.attributes.registration_supplement
        registered_meta_summary = Maybe(ctx, 'registered_meta.summary.value')
        collection = ctx.attributes.collection
        withdrawn = ctx.attributes.withdrawn
        date_registered = ctx.attributes.withdrawn
        pending_embargo_approval = ctx.attributes.pending_embargo_approval
        withdrawal_justification = Maybe(ctx.attributes, 'withdrawal_justification')
        registration = ctx.attributes.registration
        pending_withdrawal = ctx.attributes.pending_withdrawal
        type = ctx.type
        id = ctx.id
