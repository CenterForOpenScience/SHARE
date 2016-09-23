import arrow

import dateparser

from share.normalize import *  # noqa


class Person(Parser):
    given_name = ParseName(ctx.author_name).first
    family_name = ParseName(ctx.author_name).last


class DataSetPerson(Parser):
    schema = 'Person'

    given_name = ParseName(ctx.full_name).first
    family_name = ParseName(ctx.full_name).last
    suffix = tools.ParseName(ctx.full_name).suffix
    additional_name = tools.ParseName(ctx.full_name).middle

    class Extra:
        id = ctx.id


class DataSetContributor(Parser):
    schema = 'Contributor'

    order_cited = ctx('index')
    cited_name = ctx.full_name
    person = Delegate(DataSetPerson, ctx)


class Contributor(Parser):
    order_cited = ctx('index')
    cited_name = ctx.author_name
    person = Delegate(Person, ctx)


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        if 'figshare.com' in link:
            return 'provider'
        return 'misc'


class Tag(Parser):
    name = ctx.name

    class Extra:
        id = ctx.id


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class FileLink(Parser):
    schema = 'Link'
    url = ctx.download_url
    type = Static('file')

    class Extra:
        id = ctx.id
        name = ctx.name
        size = ctx.size
        thumb = ctx.thumb
        mime_type = ctx.mime_type


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class CreativeWork(Parser):
    title = ctx.title
    description = ctx.description
    contributors = Map(Delegate(Contributor), ctx.authors)
    date_published = RunPython('parse_date', ctx.published_date)
    links = Map(Delegate(ThroughLinks), ctx.url, DOI(ctx.DOI), ctx.links)

    class Extra:
        modified = RunPython('parse_date', ctx.modified_date)

    def parse_date(self, date_str):
        return arrow.get(dateparser.parse(date_str)).to('UTC').isoformat()


class DataSet(Parser):
    schema = 'CreativeWork'
    title = ctx.title
    description = ctx.description_nohtml
    date_published = RunPython('parse_date', ctx.published_date)
    contributors = Map(Delegate(DataSetContributor), ctx.owner, ctx.authors)

    links = Concat(
        Map(Delegate(ThroughLinks.using(link=Delegate(FileLink))), ctx.files),
        Map(Delegate(ThroughLinks), ctx.figshare_url, DOI(ctx.doi), DOI(ctx.publisher_doi))
    )

    tags = Map(
        Delegate(ThroughTags),
        ctx.tags,
        ctx.categories,
    )

    class Extra:
        status = ctx.status
        version = ctx.version
        total_size = ctx.total_size
        article_id = ctx.article_id
        defined_type = ctx.defined_type
        citation = ctx.publisher_citation

    def parse_date(self, date_str):
        return arrow.get(dateparser.parse(date_str)).to('UTC').isoformat()


class FigshareNormalizer(Normalizer):

    def do_normalize(self, data):
        unwrapped = self.unwrap_data(data)

        if 'files' in unwrapped:
            return DataSet(unwrapped).parse()
        return CreativeWork(unwrapped).parse()
