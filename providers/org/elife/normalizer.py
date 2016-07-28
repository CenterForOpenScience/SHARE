import datetime

from lxml import etree

from share.normalize import *
from share.normalize.utils import format_doi_as_url


def text(obj):
    if isinstance(obj, str):
        return obj
    return obj['#text']


class Link(Parser):
    url = ctx
    type = Static('doi')


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Institution(Parser):
    name = Maybe(ctx, 'institution')


class Organization(Parser):
    name = ctx['contrib']['collab']


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
    name = RunPython(text, ctx.kwd)


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Publisher(Parser):
    name = RunPython(text, ctx['publisher-name'])


class Association(Parser):
    entity = Delegate(Publisher, ctx)


class CreativeWork(Parser):

    title = RunPython(text, XPath(ctx, '//article-meta/title-group/article-title')['article-title'])
    description = RunPython(text, Maybe(XPath(ctx, '//abstract[not(@abstract-type="executive-summary")]/p[1]'), 'p'))
    date_published = ParseDate(
        RunPython('parse_date',
            XPath(ctx, '//article-meta/pub-date[@publication-format="electronic"]')['pub-date']
        )
    )
    rights = RunPython(text, XPath(ctx, '//permissions/license/license-p')['license-p']['ext-link'])
    contributors = Map(
        Delegate(Contributor),
        XPath(ctx, '//article-meta/contrib-group/contrib[name]')
    )
    publishers = Map(
        Delegate(Association),
        XPath(ctx, '//publisher-name')
    )
    organizations = Map(
        Delegate(Association.using(entity=Delegate(Organization))),
        XPath(ctx, '//article-meta/contrib-group/contrib[not(name)]')
    )
    tags = Map(
        Delegate(ThroughTags),
        XPath(ctx, '//kwd')
    )
    links = Map(
        Delegate(ThroughLinks),
        RunPython('format_doi_url', RunPython(text, XPath(ctx, '//article-id[@pub-id-type="doi"]')[0]['article-id']))
    )

    class Extra:
        article_categories = XPath(ctx, '//article-meta/atricle-categories/descendant::text()')

    def parse_date(self, ctx):
        day = ctx.get('day')
        month = ctx.get('month')
        year = ctx.get('year')
        return datetime.date(int(year), int(month), int(day))

    def format_doi_url(self, doi):
        return format_doi_as_url(self, doi)
