from share.transform.chain import ctx, ChainTransformer
from share.transform.chain import links as tools
from share.transform.chain.parsers import Parser


class SimpleWorkIdentifier(Parser):
    schema = 'WorkIdentifier'

    uri = tools.IRI(ctx)


class WorkIdentifier(Parser):
    uri = ctx.attributes.value

    class Extra:
        identifier_type = tools.Try(ctx.attributes.category)


class AgentIdentifier(Parser):
    uri = tools.IRI(ctx)


# TODO At somepoint we'll need to get Institutions as well
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

    identifiers = tools.Map(
        tools.Delegate(AgentIdentifier),
        tools.RunPython('registered', ctx.embeds.users.data.links.html),
        tools.Try(ctx.embeds.users.data.links.profile_image),
    )

    class Extra:
        locale = tools.Try(ctx.embeds.users.data.attributes.locale)
        date_registered = tools.Try(ctx.embeds.users.data.attributes.date_registered)
        active = tools.Try(ctx.embeds.users.data.attributes.active)
        timezone = tools.Try(ctx.embeds.users.data.attributes.timezone)

    def registered(self, context):
        if self.context['attributes']['unregistered_contributor']:
            return None
        return context


class Contributor(Parser):
    agent = tools.Delegate(Person, ctx)
    cited_as = tools.OneOf(
        ctx.embeds.users.data.attributes.full_name,
        ctx.embeds.users.errors[0].meta.full_name,
    )


class Creator(Contributor):
    order_cited = ctx.attributes.index


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = tools.Delegate(Tag, ctx)


class Institution(Parser):
    name = ctx.attributes.name
    identifiers = tools.Map(tools.Delegate(AgentIdentifier), ctx.links.self)

    class Extra:
        description = ctx.attributes.description


class AgentWorkRelation(Parser):
    agent = tools.Delegate(Institution, ctx)


class CreativeWork(Parser):
    title = ctx.attributes.title
    description = ctx.attributes.description
    is_deleted = tools.Static(False)
    # date_published =
    date_updated = tools.ParseDate(ctx.attributes.date_modified)
    # free_to_read_type =
    # free_to_read_date =
    # rights = tools.Try(ctx.attributes.node_license)  Doesn't seem to have an useful information
    # language =

    identifiers = tools.Concat(
        tools.Map(tools.Delegate(SimpleWorkIdentifier), ctx.links.html, ctx.links.self),
        tools.Map(tools.Delegate(WorkIdentifier), tools.Try(ctx.identifiers))
    )

    tags = tools.Map(tools.Delegate(ThroughTags), ctx.attributes.category, ctx.attributes.tags)

    class Extra:
        date_created = tools.ParseDate(ctx.attributes.date_created)


class IsPartOf(Parser):
    subject = tools.Delegate(CreativeWork, ctx)


class Project(CreativeWork):
    is_root = True
    related_works = tools.Map(tools.Delegate(IsPartOf), tools.Try(ctx.children))

    related_agents = tools.Concat(
        tools.Map(tools.Delegate(Creator), tools.Filter(lambda x: x['attributes']['bibliographic'], ctx.contributors)),
        tools.Map(tools.Delegate(Contributor), tools.Filter(lambda x: not x['attributes']['bibliographic'], ctx.contributors)),
        tools.Map(tools.Delegate(AgentWorkRelation), tools.Try(ctx.institutions)),
    )


class OSFTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Project
