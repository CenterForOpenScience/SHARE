from share.normalize import ctx
from share.normalize.parsers import Parser
from share.normalize.links import Delegate, Map, Maybe, Concat, RunPython, ParseDate


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
    url = RunPython('parse_url', ctx)
    type = RunPython('parse_type', ctx)

    def parse_url(self, ctx):
        if isinstance(ctx, str):
            return ctx
        else:
            return_id = ctx['attributes']['value']
            if ctx['attributes']['category'] == 'doi':
                return 'http://dx.doi.org/{}'.format(return_id)
            else:
                return 'http://n2t.net/ark:/{}'.format(return_id)

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
        Delegate(Association.using(entity=Delegate(Institution))),
        Maybe(ctx, 'embeds').affiliated_institutions.data
    )
    date_updated = ParseDate(ctx.attributes.date_modified)
    subject = Delegate(Tag, ctx.attributes.category)
    tags = Map(Delegate(ThroughTags), ctx.attributes.tags)
    rights = Maybe(ctx, 'attributes.node_license')
    free_to_read_date = ParseDate(Maybe(ctx.attributes, 'embargo_end_date'))
    links = Concat(
        Delegate(ThroughLinks, ctx.links.html),
        Map(Delegate(ThroughLinks), Maybe(ctx, 'embeds').identifiers.data)
    )

    class Extra:
        files = Maybe(ctx.relationships, 'files').links.related.href
        registration_schema = Maybe(ctx.relationships, 'registration_schema').links.related.href
        logs = Maybe(ctx.relationships, 'logs').links.related.href
        forks = Maybe(ctx.relationships, 'forks').links.related.href
        root = Maybe(ctx.relationships, 'root').links.related.href
        comments = Maybe(ctx.relationships, 'comments').links.related.href
        registered_from = Maybe(ctx.relationships, 'registered_from').links.related.href
        node_links = Maybe(ctx.relationships, 'node_links').links.related.href
        wikis = Maybe(ctx.relationships, 'wikis').links.related.href
        children = Maybe(ctx.relationships, 'children').links.related.href

        fork = Maybe(ctx.attributes, 'fork')
        pending_registration_approval = Maybe(ctx.relationships, 'pending_registration_approval')
        date_created = ParseDate(ctx.attributes.date_created)
        date_modified = Maybe(ctx.attributes, 'date_modified')
        registration_supplement = Maybe(ctx.attributes, 'registration_supplement')
        registered_meta_summary = Maybe(ctx, 'registered_meta.summary.value')
        collection = Maybe(ctx.attributes, 'collection')
        withdrawn = Maybe(ctx.attributes, 'withdrawn')
        date_registered = Maybe(ctx.attributes, 'withdrawn')
        pending_embargo_approval = Maybe(ctx.attributes, 'pending_embargo_approval')
        withdrawal_justification = Maybe(ctx.attributes, 'withdrawal_justification')
        registration = Maybe(ctx.attributes, 'registration')
        pending_withdrawal = Maybe(ctx.attributes, 'pending_withdrawal')
        type = ctx.type
        id = ctx.id
