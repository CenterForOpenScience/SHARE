from share.normalize import ctx
from share.normalize import tools
from share.normalize.parsers import Parser
from share.normalize.utils import format_doi_as_url



class Person(Parser):
    given_name = tools.ParseName(ctx.creator).first
    family_name = tools.ParseName(ctx.creator).last
    additional_name = tools.ParseName(ctx.creator).middle
    suffix = tools.ParseName(ctx.creator).suffix


class Contributor(Parser):
    person = tools.Delegate(Person, ctx)
    cited_name = ctx.creator
    order_cited = ctx('index')


class Tag(Parser):
    name = ctx


class Link(Parser):
    url = ctx.value
    type = tools.RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if self.config.home_page and self.config.home_page in link['value']:
            return 'provider'
        if 'doi' in link['value']:
            return 'doi'
        return 'misc'


class ThroughLinks(Parser):
    link = tools.Delegate(Link, ctx)


class Association(Parser):
    pass


class Publisher(Parser):
    name = ctx


class Publication(Parser):
    title = ctx.title
    contributors = tools.Map(tools.Delegate(Contributor), ctx.creators)
    description = ctx.abstract
    date_published = tools.ParseDate(ctx.publicationDate)
    rights = ctx.copyright
    subject = tools.Delegate(Tag, tools.Maybe(ctx, 'genre'))

    links = tools.Map(
        tools.Delegate(ThroughLinks),
        ctx.url
    )

    publishers = tools.Map(
        tools.Delegate(Association.using(entity=tools.Delegate(Publisher))),
        ctx.publisher
    )

    class Extra:
        publication_name = ctx.publicationName
        issn = ctx.issn
        openaccess = ctx.openaccess
        journalid = ctx.journalid
        volume = ctx.volume
        number = ctx.number
        issuetype = ctx.issuetype
        topical_collection = ctx.topicalCollection
        starting_page = ctx.startingPage
        identifier = ctx.identifier
