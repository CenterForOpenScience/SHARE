import datetime

from lxml import etree

from share.normalize import *
from share.normalize.utils import format_doi_as_url


class Link(Parser):
    url = ctx
    type = Static('doi')


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Institution(Parser):
    name = Maybe(ctx, 'institution')


class Affiliation(Parser):
    entity = Delegate(Institution)


class Person(Parser):
    given_name = ctx.contrib.name['given-names']
    family_name = ctx.contrib.name.surname
    affiliations = Map(Delegate(Affiliation), Maybe(ctx.contrib, 'aff'))


class Contributor(Parser):
    order_cited = ctx('index')
    cited_name = Join(Concat(ctx.contrib.name['given-names'], ctx.contrib.name.surname), joiner=' ')
    person = Delegate(Person, ctx)


class Tag(Parser):
    name = Maybe(ctx.kwd, '#text')


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Publisher(Parser):
    name = ctx['publisher-name']['#text']


class Association(Parser):
    entity = Delegate(Publisher, ctx)


class CreativeWork(Parser):

    def parse_date(self, ctx):
        day = ctx.get('day')
        month = ctx.get('month')
        year = ctx.get('year')
        return datetime.date(int(year), int(month), int(day))

    def format_doi_url(self, doi):
        return format_doi_as_url(self, doi)

    title = XPath(ctx, '//article-meta/title-group/article-title')['article-title']['#text']
    description = Maybe(XPath(ctx, '//abstract[not(@abstract-type="executive-summary")]/p[1]'), 'p')['#text']
    date_published = ParseDate(
        RunPython('parse_date',
                  XPath(ctx, '//article-meta/pub-date[@publication-format="electronic"]')['pub-date']
        )
    )
    rights = XPath(ctx, '//permissions/license/license-p')['license-p']['ext-link']['#text']
    contributors = Map(
        Delegate(Contributor),
        XPath(ctx, '//article-meta/contrib-group/contrib')
    )
    publishers = Map(
        Delegate(Association),
        XPath(ctx, '//publisher-name')
    )
    tags = Map(
        Delegate(ThroughTags),
        XPath(ctx, '//kwd')
    )
    links = Map(
        Delegate(ThroughLinks),
        RunPython('format_doi_url', XPath(ctx, '//article-id[@pub-id-type="doi"]')[0]['article-id']['#text'])
    )

    class Extra:
        article_categories = XPath(ctx, '//article-meta/atricle-categories/descendant::text()')
