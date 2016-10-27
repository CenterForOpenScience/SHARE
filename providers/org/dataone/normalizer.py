from share.normalize import *


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'cn.dataone.org' in link:
            return 'provider'
        return 'misc'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix


class Contributor(Parser):
    order_cited = ctx('index')
    cited_name = ctx
    person = Delegate(Person, ctx)


class CreativeWork(Parser):
    # https://releases.dataone.org/online/api-documentation-v2.0/design/SearchMetadata.html#attribute-descriptions-and-notes
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
            Maybe(XPath(ctx, "arr[@name='origin']"), 'arr').str, # TODO or 'originator'?
        )
    )

    tags = Map(
        Delegate(ThroughTags),
        Maybe(XPath(ctx, "arr[@name='keywords']"), 'arr').str
    )
    links = Map(
        Delegate(ThroughLinks),
        Maybe(XPath(ctx, "str[@name='dataUrl']"), 'str')['#text']
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
