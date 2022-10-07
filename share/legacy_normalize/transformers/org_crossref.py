from share.legacy_normalize.transform.chain import *
from share.legacy_normalize.transform.chain import links


class AgentIdentifier(Parser):
    uri = IRI(ctx)


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class RelatedAgent(Parser):
    schema = GuessAgentType(OneOf(ctx.name, ctx), default='organization')
    name = OneOf(ctx.name, ctx)
    identifiers = Map(
        Delegate(AgentIdentifier),
        Try(ctx.DOI)
    )

    # class Extra:
    #     doi = Maybe(ctx, 'DOI')
    #     award = Maybe(ctx, 'award')
    #     doi_asserted_by = Maybe(ctx, 'doi-asserted-by')


class Funder(Parser):
    agent = Delegate(RelatedAgent, ctx)


class Publisher(Parser):
    agent = Delegate(RelatedAgent, ctx)


class IsAffiliatedWith(Parser):
    related = Delegate(RelatedAgent, ctx)


class Person(Parser):
    given_name = Maybe(ctx, 'given')
    family_name = Maybe(ctx, 'family')

    identifiers = Map(
        Delegate(AgentIdentifier),
        Try(ctx.ORCID)
    )

    related_agents = Map(Delegate(IsAffiliatedWith), Maybe(ctx, 'affiliation'))


class Creator(Parser):
    agent = Delegate(Person, ctx)
    order_cited = ctx('index')

    cited_as = links.Join(
        Concat(
            Maybe(ctx, 'given'),
            Maybe(ctx, 'family')
        ),
        joiner=' '
    )


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class CreativeWork(Parser):
    """
    Documentation for CrossRef's metadata can be found here:
    https://github.com/CrossRef/rest-api-doc/blob/master/api_format.md
    """

    def get_schema(self, type):
        return {
            'journal-article': 'Article',
            'book': 'Book',
            'proceedings-article': 'ConferencePaper',
            'dataset': 'Dataset',
            'dissertation': 'Dissertation',
            'preprint': 'Preprint',
            'report': 'Report',
        }.get(type) or 'CreativeWork'

    schema = RunPython('get_schema', ctx.type)

    title = Maybe(ctx, 'title')[0]
    description = Maybe(ctx, 'subtitle')[0]
    date_updated = ParseDate(Try(ctx.deposited['date-time']))

    identifiers = Map(
        Delegate(WorkIdentifier),
        ctx.DOI,
        # Links do not appear to be unique
        # Map(OneOf(ctx.URL, ctx), Try(ctx.link)),
        Try(IRI(ctx['alternative-id']))
    )

    related_agents = Concat(
        Map(Delegate(Creator), Try(ctx.author)),
        Map(Delegate(Publisher), ctx.publisher),
        Map(Delegate(Funder), Filter(lambda x: isinstance(x, str) or 'name' in x, Try(ctx.funder))),
    )

    # TODO These are "a controlled vocabulary from Sci-Val", map to Subjects!
    tags = Map(
        Delegate(ThroughTags),
        Maybe(ctx, 'subject')
    )

    class Extra:
        alternative_id = Maybe(ctx, 'alternative-id')
        archive = Maybe(ctx, 'archive')
        article_number = Maybe(ctx, 'article-number')
        chair = Maybe(ctx, 'chair')
        container_title = Maybe(ctx, 'container-title')
        date_created = ParseDate(Try(ctx.created['date-time']))
        date_published = Maybe(ctx, 'issued')
        editor = Maybe(ctx, 'editor')
        licenses = Maybe(ctx, 'license')
        isbn = Maybe(ctx, 'isbn')
        issn = Maybe(ctx, 'issn')
        issue = Maybe(ctx, 'issue')
        member = Maybe(ctx, 'member')
        page = Maybe(ctx, 'page')
        published_online = Maybe(ctx, 'published-online')
        published_print = Maybe(ctx, 'published-print')
        reference_count = ctx['reference-count']
        subjects = Maybe(ctx, 'subject')
        subtitles = Maybe(ctx, 'subtitle')
        titles = ctx.title
        translator = Maybe(ctx, 'translator')
        type = ctx.type
        volume = Maybe(ctx, 'volume')


class CrossrefTransformer(ChainTransformer):
    VERSION = 1
    root_parser = CreativeWork
