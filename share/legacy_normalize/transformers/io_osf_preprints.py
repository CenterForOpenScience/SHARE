from share.legacy_normalize.transform.chain import ctx, links as tools, ChainTransformer
from share.legacy_normalize.transform.chain.parsers import Parser

from . import io_osf as osf


# class PersonIdentifier(Parser):
#     uri = ctx

# class Person(Parser):
#     given_name = OneOf(
#         ctx.embeds.users.data.attributes.given_name,
#         ctx.embeds.users.errors[0].meta.given_name,
#     )
#     family_name = OneOf(
#         ctx.embeds.users.data.attributes.family_name,
#         ctx.embeds.users.errors[0].meta.family_name,
#     )
#     additional_name = OneOf(
#         ctx.embeds.users.data.attributes.middle_names,
#         ctx.embeds.users.errors[0].meta.middle_names,
#     )
#     suffix = OneOf(
#         ctx.embeds.users.data.attributes.suffix,
#         ctx.embeds.users.errors[0].meta.suffix,
#     )
#     personidentifiers = Map(Delegate(PersonIdentifier), Try(ctx.embeds.users.data.links.html))

#     class Extra:
#         nodes = Try(ctx.embeds.users.data.relationships.nodes.links.related.href)
#         locale = Try(ctx.embeds.users.data.attributes.locale)
#         date_registered = Try(ctx.embeds.users.data.attributes.date_registered)
#         active = Try(ctx.embeds.users.data.attributes.active)
#         timezone = Try(ctx.embeds.users.data.attributes.timezone)
#         profile_image = OneOf(
#             ctx.embeds.users.data.links.profile_image,
#             ctx.embeds.users.errors[0].meta.profile_image
#         )


# class Contributor(Parser):
#     person = Delegate(Person, ctx)
#     order_cited = ctx.attributes.index
#     bibliographic = ctx.attributes.bibliographic
#     cited_name = OneOf(
#         ctx.embeds.users.data.attributes.full_name,
#         ctx.embeds.users.errors[0].meta.full_name,
#     )


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = tools.Delegate(Tag, ctx)


# class Institution(Parser):
#     name = ctx.attributes.name
#     url = ctx.links.self

#     class Extra:
#         nodes = ctx.relationships.nodes.links.related.href
#         users = ctx.relationships.users.links.related.href
#         registrations = ctx.relationships.registrations.links.related.href
#         description = ctx.attributes.description


class Subject(Parser):
    name = ctx.text


class ThroughSubjects(Parser):
    subject = tools.Delegate(Subject, ctx)


class WorkIdentifier(Parser):
    uri = tools.IRI(ctx)


class Preprint(osf.Project):
    description = tools.Try(ctx.attributes.abstract)
    date_updated = tools.ParseDate(ctx.attributes.date_modified)
    date_published = tools.ParseDate(ctx.attributes.date_created)
    # NOTE: OSF has a direct mapping to SHARE's taxonomy. Subjects() is not needed
    subjects = tools.Map(tools.Delegate(ThroughSubjects), ctx.attributes.subjects)
    identifiers = tools.Map(
        tools.Delegate(WorkIdentifier),
        ctx.links.self,
        ctx.links.html,
        tools.Try(ctx.links.doi)
    )
    tags = tools.Map(tools.Delegate(ThroughTags), tools.Try(ctx.attributes.tags))
    rights = tools.Try(ctx.attributes.node_license)

    related_works = tools.Static([])
    related_agents = tools.Concat(
        tools.Map(tools.Delegate(osf.Creator), tools.Filter(lambda x: x['attributes']['bibliographic'], ctx.contributors)),
        tools.Map(tools.Delegate(osf.Contributor), tools.Filter(lambda x: not x['attributes']['bibliographic'], ctx.contributors)),
    )


class PreprintTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Preprint
