from share.normalize import *  # noqa
from share.normalize.utils import format_doi_as_url


class Person(Parser):
    given_name = ParseName(ctx).first
    family_name = ParseName(ctx).last
    additional_name = ParseName(ctx).middle
    suffix = ParseName(ctx).suffix


class Contributor(Parser):
    person = Delegate(Person, ctx)
    cited_name = ctx
    order_cited = ctx('index')


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        return 'eissn'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Publisher(Parser):
    name = ctx


class Association(Parser):
    entity = Delegate(Publisher, ctx)


class Publication(Parser):

    def format_doi_as_url(self, doi):
        return format_doi_as_url(self, doi)

    title = XPath(ctx, "str[@name='title_display']").str['#text']
    description = XPath(ctx, "arr[@name='abstract']/str").str
    contributors = Map(
        Delegate(Contributor),
        XPath(ctx, "arr[@name='author_display']").arr.str
    )
    publishers = Map(
        Delegate(Association),
        XPath(ctx, "str[@name='journal']").str['#text']
    )
    links = Map(
        Delegate(ThroughLinks),
        RunPython(
            'format_doi_as_url',
            XPath(ctx, "str[@name='id']").str['#text'],
        ),
        XPath(ctx, "str[@name='eissn']").str['#text']
    )
    date_published = ParseDate(XPath(ctx, "date[@name='publication_date']").date['#text'])

    class Extra:
        article_type = XPath(ctx, "str[@name='article_type']").str['#text']
        score = XPath(ctx, "float[@name='score']").float['#text']
