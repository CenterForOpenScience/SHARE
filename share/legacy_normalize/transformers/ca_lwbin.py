from share.legacy_normalize.transform.chain import *


class AgentIdentifier(Parser):
    uri = IRI(ctx)


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class Tag(Parser):
    name = ctx.name


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Maintainer(Parser):
    schema = GuessAgentType(ctx.maintainer)
    name = ctx.maintainer
    identifiers = Map(Delegate(AgentIdentifier), ctx.maintainer_email)


class Author(Parser):
    schema = GuessAgentType(ctx.author)
    name = ctx.author
    identifiers = Map(Delegate(AgentIdentifier), ctx.author_email)


class Organization(Parser):
    schema = RunPython('org_or_consortium', ctx.is_organization)

    name = ctx.title
    identifiers = Map(Delegate(AgentIdentifier), RunPython('get_urls', ctx))

    def org_or_consortium(self, is_org):
        return 'Organization' if is_org else 'Consortium'

    def get_urls(self, context):
        return [
            'http://130.179.67.140/{type}/{id}'.format(**context),
            'http://130.179.67.140/uploads/group/{image_url}'.format(**context),
        ]

    class Extra:
        description = ctx.description


class Creator(Parser):
    agent = Delegate(Author, ctx)


class CreatorMaintainer(Parser):
    schema = 'creator'
    agent = Delegate(Maintainer, ctx)


class Contributor(Parser):
    agent = Delegate(Organization, ctx)


class CreativeWork(Parser):
    schema = RunPython('get_schema', ctx.type)

    title = ctx.title
    description = ctx.notes
    is_deleted = ctx.private
    date_published = ParseDate(ctx.metadata_created)
    date_updated = ParseDate(ctx.metadata_modified)
    free_to_read_type = Try(IRI(ctx.license_url))
    # free_to_read_date
    rights = ctx.license_title
    # language

    tags = Map(Delegate(ThroughTags), ctx.tags)
    identifiers = Map(
        Delegate(WorkIdentifier),
        RunPython('get_url', ctx),
        RunPython('get_dois', ctx.extras),
        Try(IRI(ctx.url), exceptions=(InvalidIRI, )),
    )

    related_agents = Concat(
        Map(Delegate(Creator), Filter(lambda x: x.get('author'), ctx)),
        Map(Delegate(CreatorMaintainer), Filter(lambda x: x.get('maintainer'), ctx)),
        Map(Delegate(Contributor), ctx.organization, ctx.groups)
    )
    # related_works = ShareManyToManyField('AbstractCreativeWork', through='AbstractWorkRelation', through_fields=('subject', 'related'), symmetrical=False)

    class Extra:
        revision_timestamp = ParseDate(ctx.revision_timestamp)
        state = ctx.state
        version = ctx.version

    def get_url(self, context):
        return 'http://130.179.67.140/{type}/{id}'.format(**context)

    def get_dois(self, context):
        # Sometimes values can be "to be added" or similar
        # There also seems to be a couple dx.doi.org/11.xxx/... floating around
        return [x['value'] for x in context if x['key'] == 'DOI' and '10.0' in x['value']]

    def get_schema(self, type):
        return {
            'dataset': 'DataSet',
        }[type]


class LWBINTransformer(ChainTransformer):
    VERSION = 1
    root_parser = CreativeWork
