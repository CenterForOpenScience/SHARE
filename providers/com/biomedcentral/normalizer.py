from share.normalize import *  # noqa


class Link(Parser):
    url = ctx.value
    type = RunPython('get_link_type', ctx.value)

    def get_link_type(self, link):
        if 'dx.doi' in link:
            return 'doi'
        if 'springer' in link:
            return 'provider'
        return 'misc'

    class Extra:
        format = ctx.format
        platform = ctx.platform


class Tag(Parser):
    name = ctx


class Publisher(Parser):
    name = ctx


class Association(Parser):
    entity = Delegate(Publisher)


class Person(Parser):
    given_name = ParseName(ctx.creator).first
    family_name = ParseName(ctx.creator).last
    additional_name = ParseName(ctx.creator).middle
    suffix = ParseName(ctx.creator).suffix


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Contributor(Parser):
    person = Delegate(Person, ctx)
    cited_name = ctx.creator
    order_cited = ctx('index')


class Article(Parser):
    title = ctx.title
    contributors = Map(Delegate(Contributor), ctx.creators)
    description = ctx.abstract
    date_published = ParseDate(ctx.publicationDate)
    tags = Map(Delegate(ThroughTags), Maybe(ctx, 'genre'))
    links = Map(Delegate(ThroughLinks), ctx.url)
    publishers = Map(Delegate(Association), Maybe(ctx, 'publicationName'), Maybe(ctx, 'publisher'))
    rights = ctx.copyright

    class Extra:
        openaccess = ctx.openaccess
        ending_page = Try(ctx.endingPage)
        issue_type = ctx.issuetype
        number = ctx.number
        starting_page = ctx.startingPage
        topicalCollection = ctx.topicalCollection
        journalid = ctx.journalid
        issn = Try(ctx.issn)
