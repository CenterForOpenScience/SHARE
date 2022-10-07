from share.legacy_normalize.transform.chain import *  # noqa


class AgentIdentifier(Parser):
    uri = IRI(ctx)


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class Person(Parser):
    name = ctx


class Creator(Parser):
    agent = Delegate(Person, ctx)
    cited_as = ctx
    order_cited = ctx('index')


class Organization(Parser):
    name = XPath(ctx, "str[@name='journal']").str['#text']
    identifiers = Map(
        Delegate(AgentIdentifier),
        Map(Try(IRI(), exceptions=(InvalidIRI, )), XPath(ctx, "str[@name='eissn']").str['#text'])
    )


class Publisher(Parser):
    agent = Delegate(Organization, ctx)


class Article(Parser):
    title = XPath(ctx, "str[@name='title_display']").str['#text']
    description = XPath(ctx, "arr[@name='abstract']/str").str
    # is_deleted
    date_published = ParseDate(XPath(ctx, "date[@name='publication_date']").date['#text'])
    date_updated = ParseDate(XPath(ctx, "date[@name='publication_date']").date['#text'])
    # free_to_read_type
    # free_to_read_data
    # rights
    # language

    # subjects
    # tags

    identifiers = Map(
        Delegate(WorkIdentifier),
        XPath(ctx, "str[@name='id']").str['#text'],
    )
    related_agents = Concat(
        Map(Delegate(Creator), Try(XPath(ctx, "arr[@name='author_display']").arr.str)),
        Map(Delegate(Publisher), ctx)
    )
    # related_works

    class Extra:
        article_type = XPath(ctx, "str[@name='article_type']").str['#text']


class PLoSTransformer(ChainTransformer):
    VERSION = 1
    root_parser = Article
