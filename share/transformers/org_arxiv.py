from share.transform.chain import ctx, ChainTransformer
from share.transform.chain import links as tools
from share.transform.chain.parsers import Parser


class WorkIdentifier(Parser):
    uri = tools.IRI(ctx)


class Organization(Parser):
    schema = tools.GuessAgentType(ctx)

    name = tools.RunPython('get_name', ctx)
    location = tools.RunPython('get_location', ctx)

    def get_name(self, context):
        return context.split(',')[0]

    def get_location(self, context):
        spl = context.partition(',')
        if len(spl) > 1:
            return spl[-1]
        return None


class IsAffiliatedWith(Parser):
    related = tools.Delegate(Organization, ctx)


class Person(Parser):
    name = ctx.name

    related_agents = tools.Map(
        tools.Delegate(IsAffiliatedWith),
        tools.Try(ctx['arxiv:affiliation'])
    )


class Creator(Parser):
    order_cited = ctx('index')
    cited_as = ctx.name
    agent = tools.Delegate(Person, ctx)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = tools.Delegate(Tag, ctx)


class Subject(Parser):
    name = ctx


class ThroughSubjects(Parser):
    subject = tools.Delegate(Subject, ctx)


class Preprint(Parser):
    title = ctx.entry.title
    description = ctx.entry.summary

    date_published = tools.ParseDate(ctx.entry.published)
    date_updated = tools.ParseDate(ctx.entry.updated)
    # free_to_read_type
    # free_to_read_date
    # rights
    # language
    subjects = tools.Map(
        tools.Delegate(ThroughSubjects),
        tools.Subjects(tools.Map(ctx['@term'], ctx.entry.category)),
    )
    tags = tools.Map(
        tools.Delegate(ThroughTags),
        tools.Map(ctx['@term'], ctx.entry.category),
    )
    related_agents = tools.Concat(
        tools.Map(tools.Delegate(Creator), ctx.entry.author),
    )
    # related_works
    identifiers = tools.Map(tools.Delegate(WorkIdentifier), tools.Try(ctx.entry['arxiv:doi']), ctx.entry.id)

    class Extra:
        resource_id = ctx.entry.id
        journal_ref = tools.Try(ctx.entry['arxiv:journal_ref'])
        comment = tools.Try(ctx.entry['arxiv:comment'])
        primary_category = tools.Try(ctx.entry['arxiv:primary_category'])


class ArxivTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Preprint
