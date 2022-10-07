from share.legacy_normalize.transform.chain import *  # noqa


class AgentIdentifier(Parser):
    uri = IRI(ctx)


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Person(Parser):
    given_name = ParseName(ctx.creator).first
    family_name = ParseName(ctx.creator).last
    additional_name = ParseName(ctx.creator).middle
    suffix = ParseName(ctx.creator).suffix


class Creator(Parser):
    agent = Delegate(Person, ctx)
    cited_as = ctx.creator
    order_cited = ctx('index')


class Organization(Parser):
    name = ctx.publisher
    identifiers = Map(Delegate(AgentIdentifier), Try(IRI(ctx.issn), exceptions=(InvalidIRI, )))

    class Extra:
        issn = Try(ctx.issn)


class Publisher(Parser):
    agent = Delegate(Organization, ctx)

    class Extra:
        publication_name = ctx.publicationName


class Article(Parser):
    title = ctx.title
    description = ctx.abstract
    rights = ctx.copyright
    date_published = ParseDate(ctx.publicationDate)
    date_updated = ParseDate(ctx.publicationDate)

    identifiers = Map(
        Delegate(WorkIdentifier),
        ctx.doi,
        ctx.identifier,
        Map(ctx.value, ctx.url),
    )

    related_agents = Concat(
        Map(Delegate(Creator), ctx.creators),
        Map(Delegate(Publisher), ctx)
    )

    tags = Map(Delegate(ThroughTags), ctx.genre)

    class Extra:
        openaccess = ctx.openaccess
        ending_page = Try(ctx.endingPage)
        issue_type = Try(ctx.issuetype)
        number = ctx.number
        starting_page = ctx.startingPage
        topicalCollection = Try(ctx.topicalCollection)
        journalid = Try(ctx.journalid)
        issn = Try(ctx.issn)


class SpringerTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Article
