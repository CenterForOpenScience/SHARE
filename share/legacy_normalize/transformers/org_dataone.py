from share.legacy_normalize.transform.chain import *


class WorkIdentifier(Parser):
    uri = ctx


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Agent(Parser):
    schema = GuessAgentType(ctx)

    name = ctx


class Person(Parser):
    name = ctx


class Contributor(Parser):
    agent = Delegate(Person, ctx)
    cited_as = ctx


class Creator(Contributor):
    order_cited = ctx('index')


class RelatedWork(Parser):
    schema = 'DataSet'

    identifiers = Map(
        Delegate(WorkIdentifier),
        IRI(ctx)
    )


class IsPartOf(Parser):
    related = Delegate(RelatedWork, ctx)


class IsDocumentedBy(Parser):
    schema = 'Documents'

    subject = Delegate(RelatedWork, ctx)


class Documents(Parser):
    related = Delegate(RelatedWork, ctx)


class DataSet(Parser):
    # https://releases.dataone.org/online/api-documentation-v2.0/design/SearchMetadata.html
    title = Try(XPath(ctx, "str[@name='title']").str['#text'])
    description = Try(XPath(ctx, "str[@name='abstract']").str['#text'])
    date_updated = ParseDate(Try(XPath(ctx, "date[@name='dateModified']").date['#text']))
    date_published = ParseDate(Try(XPath(ctx, "date[@name='datePublished']").date['#text']))

    related_agents = Concat(
        Map(
            Delegate(Creator),
            Maybe(XPath(ctx, "str[@name='author']"), 'str')['#text'],
        ),
        Map(
            Delegate(Contributor),
            Maybe(XPath(ctx, "arr[@name='investigator']"), 'arr').str,
        ),
        Map(
            Delegate(Contributor.using(agent=Delegate(Agent))),
            Maybe(XPath(ctx, "arr[@name='origin']"), 'arr').str,
        )
    )

    related_works = Concat(
        # TODO Maybe re introduce later with more research
        # Map(
        #     Delegate(IsPartOf),
        #     Maybe(XPath(ctx, "arr[@name='resourceMap']"), 'arr').str
        # ),
        Map(
            Delegate(Documents),
            Maybe(XPath(ctx, "arr[@name='documents']"), 'arr').str
        ),
        Map(
            Delegate(IsDocumentedBy),
            Maybe(XPath(ctx, "arr[@name='isDocumentedBy']"), 'arr').str
        ),
    )

    identifiers = Map(
        Delegate(WorkIdentifier),
        Map(
            IRI(urn_fallback=True),
            Maybe(XPath(ctx, "str[@name='dataUrl']"), 'str')['#text'],
            Maybe(XPath(ctx, "str[@name='identifier']"), 'str')['#text']
        )
    )

    tags = Map(
        Delegate(ThroughTags),
        Maybe(XPath(ctx, "arr[@name='keywords']"), 'arr').str
    )

    class Extra:
        datasource = Maybe(XPath(ctx, "str[@name='datasource']"), 'str')['#text']
        datePublished = Maybe(XPath(ctx, "date[@name='datePublished']"), 'date')['#text']
        dateUploaded = Maybe(XPath(ctx, "date[@name='dateUploaded']"), 'date')['#text']
        fileID = Maybe(XPath(ctx, "str[@name='fileID']"), 'str')['#text']
        formatId = Maybe(XPath(ctx, "str[@name='formatId']"), 'str')['#text']
        formatType = Maybe(XPath(ctx, "str[@name='formatType']"), 'str')['#text']
        id = Maybe(XPath(ctx, "str[@name='id']"), 'str')['#text']
        identifier = Maybe(XPath(ctx, "str[@name='identifier']"), 'str')['#text']


class DataoneTransformer(ChainTransformer):
    VERSION = 1
    root_parser = DataSet
