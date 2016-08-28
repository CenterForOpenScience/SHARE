import furl

from share.normalize.parsers import Parser
from share.normalize.normalizer import Normalizer
from share.normalize import Delegate, RunPython, Map, ctx, Try, ParseDate, OneOf


class Identifier(Parser):
    url = ctx
    base_url = RunPython('get_base_url', ctx)

    def get_base_url(self, url):
        url = furl.furl(url)
        return '{}://{}'.format(url.scheme, url.host)


class ThroughIdentifiers(Parser):
    identifier = Delegate(Identifier, ctx)


class Person(Parser):
    given_name = OneOf(
        ctx.embeds.users.data.attributes.given_name,
        ctx.embeds.users.errors[0].meta.given_name,
    )
    family_name = OneOf(
        ctx.embeds.users.data.attributes.family_name,
        ctx.embeds.users.errors[0].meta.family_name,
    )
    additional_name = OneOf(
        ctx.embeds.users.data.attributes.middle_names,
        ctx.embeds.users.errors[0].meta.middle_names,
    )
    suffix = OneOf(
        ctx.embeds.users.data.attributes.suffix,
        ctx.embeds.users.errors[0].meta.suffix,
    )

    identifiers = Map(
        Delegate(ThroughIdentifiers),
        Try(ctx.embeds.users.data.links.html),
        Try(ctx.embeds.users.data.links.profile_image),
        Try(ctx.embeds.users.errors[0].meta.profile_image)
    )

    class Extra:
        nodes = Try(ctx.embeds.users.data.relationships.nodes.links.related.href)
        locale = Try(ctx.embeds.users.data.attributes.locale)
        date_registered = Try(ctx.embeds.users.data.attributes.date_registered)
        active = Try(ctx.embeds.users.data.attributes.active)
        timezone = Try(ctx.embeds.users.data.attributes.timezone)
        profile_image = Try(ctx.embeds.users.data.links.profile_image)


class Contributor(Parser):
    person = Delegate(Person, ctx)
    order_cited = ctx.attributes.index
    bibliographic = ctx.attributes.bibliographic
    cited_name = OneOf(
        ctx.embeds.users.data.attributes.full_name,
        ctx.embeds.users.errors[0].meta.full_name,
    )


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


class Publisher(Parser):
    name = ctx


class Association(Parser):
    pass


class Subject(Parser):
    name = ctx.text


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        else:
            return 'provider'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class ThroughSubjects(Parser):
    subject = Delegate(Subject, ctx)


class Preprint(Parser):
    title = ctx.attributes.title
    description = Try(ctx.attributes.abstract)
    contributors = Map(Delegate(Contributor), ctx.contributors)
    date_updated = ParseDate(ctx.attributes.date_modified)
    date_published = ParseDate(ctx.attributes.date_created)
    # NOTE: OSF has a direct mapping to SHARE's taxonomy. Subjects() is not needed
    subjects = Map(Delegate(ThroughSubjects), ctx.attributes.subjects)
    links = Map(
        Delegate(ThroughLinks),
        ctx.links.self,
        ctx.links.html,
        Try(ctx.links.doi)
    )
    tags = Map(Delegate(ThroughTags), Try(ctx.attributes.tags))
    rights = Try(ctx.attributes.node_license)

    class Extra:
        files = ctx.relationships.files.links.related.href
        type_soc = ctx.type
        id_soc = ctx.id
        doi_plain = ctx.attributes.doi


class PreprintNormalizer(Normalizer):

    def do_normalize(self, data):
        unwrapped = self.unwrap_data(data)

        return Preprint(unwrapped).parse()
