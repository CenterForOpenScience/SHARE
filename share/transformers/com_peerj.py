from share.transform.chain import ChainTransformer, Parser, Delegate, RunPython, ParseDate, ParseName, Map, ctx, Try, Subjects, IRI, Concat


class Subject(Parser):
    name = ctx


class ThroughSubjects(Parser):
    subject = Delegate(Subject, ctx)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Organization(Parser):
    name = ctx


class Publisher(Parser):
    agent = Delegate(Organization, ctx)


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last


class Creator(Parser):
    agent = Delegate(Person, ctx)
    cited_as = ctx
    order_cited = ctx('index')


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class Article(Parser):
    title = ctx.title
    description = Try(ctx.description)
    language = ctx.language
    date_published = ParseDate(ctx.date)
    date_updated = ParseDate(ctx.date)

    identifiers = Map(
        Delegate(WorkIdentifier),
        ctx.doi,
        ctx.pdf_url,
        ctx.fulltext_html_url,
        RunPython(lambda x: 'https://www.ncbi.nlm.nih.gov/pubmed/{}'.format(x) if x else None, Try(ctx.identifiers.pubmed)),
        RunPython(lambda x: 'https://www.ncbi.nlm.nih.gov/pmc/articles/{}'.format(x) if x else None, Try(ctx.identifiers.pmc)),
    )

    subjects = Map(Delegate(ThroughSubjects), Subjects(ctx.subjects))
    tags = Map(Delegate(ThroughTags), Try(ctx.keywords), Try(ctx.subjects))

    related_agents = Concat(
        Map(Delegate(Creator), ctx.author),
        Map(Delegate(Publisher), ctx.publisher),
    )

    class Extra:
        volume = Try(ctx.volume)
        journal_title = Try(ctx.journal_title)
        journal_abbrev = Try(ctx.journal_abbrev)
        description_html = Try(ctx['description-html'])
        issn = Try(ctx.issn)


class Preprint(Article):

    class Extra:
        modified = ParseDate(ctx.date)
        subjects = ctx.subjects
        identifiers = Try(ctx.identifiers)
        emails = Try(ctx.author_email)
        description_html = Try(ctx['description-html'])


class PeerJTransformer(ChainTransformer):
    VERSION = 1

    def get_root_parser(self, unwrapped, emitted_type=None, **kwargs):
        if emitted_type == 'preprint':
            return Preprint
        return Article
