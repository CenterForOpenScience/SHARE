from share.transform.chain import *  # noqa


class AgentIdentifier(Parser):
    uri = IRI(ctx)


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class Person(Parser):
    name = ctx.full_name
    identifiers = Map(
        Delegate(AgentIdentifier),
        ctx.orcid_id,
        RunPython(lambda x: 'http://figshare.com/authors/{url_name}/{id}'.format(**x), ctx)
    )


class Creator(Parser):
    agent = Delegate(Person, ctx)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class CreativeWork(Parser):
    schema = RunPython('get_schema', ctx.defined_type)
    FIGSHARE_TYPES = ['figure', 'media', 'dataset', 'fileset', 'poster', 'paper', 'presentation', 'thesis', 'code', 'metadata']

    title = ctx.title
    description = ctx.description
    is_deleted = RunPython(lambda x: not x, ctx.is_active)
    date_published = ParseDate(ctx.published_date)
    date_updated = ParseDate(ctx.modified_date)
    free_to_read_type = IRI(ctx.license.url)

    related_agents = Map(Delegate(Creator), ctx.authors)

    identifiers = Map(Delegate(WorkIdentifier), ctx.doi, ctx.url, ctx.figshare_url)

    tags = Map(
        Delegate(ThroughTags),
        ctx.tags,
        Map(ctx.title, ctx.categories)
    )

    class Extra:
        files = ctx.files
        version = ctx.version
        thumb = ctx.thumb
        embargo_date = ctx.embargo_date
        embargo_reason = ctx.embargo_reason
        embargo_type = ctx.embargo_type
        citation = ctx.citation
        defined_type = ctx.defined_type

    def get_schema(self, defined_type):
        return {
            'fileset': 'Project',
            'figure': 'CreativeWork',
            'poster': 'Poster',
            'code': 'Software',
            'dataset': 'DataSet',
        }[self.FIGSHARE_TYPES[defined_type - 1]]


class FigshareV2Transformer(ChainTransformer):
    VERSION = 1
    root_parser = CreativeWork
