from share.normalize.normalizer import Normalizer

from share.normalize.parsers import Parser
from share.normalize import Delegate, RunPython, Map, ctx, Try, ParseDate


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
    contributors = Map(Delegate(Contributor), ctx['contributors'])
    date_updated = ParseDate(ctx.attributes.date_modified)
    date_published = ParseDate(ctx.attributes.date_created)
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
