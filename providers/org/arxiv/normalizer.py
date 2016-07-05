from share.normalize import ctx
from share.normalize import tools
from share.normalize.parsers import Parser
from share.normalize.utils import format_doi_as_url


class Link(Parser):
    url = tools.RunPython('format_doi', ctx)
    # identifier will always be DOI
    type = tools.Static('doi')

    def format_doi(self, doi):
        return format_doi_as_url(self, doi)


class ThroughLinks(Parser):
    link = tools.Delegate(Link, ctx)


class Organization(Parser):
    name = ctx['#text']


class Affiliation(Parser):
    pass


class Person(Parser):
    given_name = tools.ParseName(ctx.name).first
    family_name = tools.ParseName(ctx.name).last
    additional_name = tools.ParseName(ctx.name).middle
    suffix = tools.ParseName(ctx.name).suffix
    affiliations = tools.Map(
        tools.Delegate(Affiliation.using(entity=tools.Delegate(Organization))),
        tools.Maybe(ctx, 'arxiv:affiliation')
    )


class Contributor(Parser):
    order_cited = ctx('index')
    cited_name = ctx.name
    person = tools.Delegate(Person, ctx)


class Tag(Parser):
    name = ctx['@term']


class ThroughTags(Parser):
    tag = tools.Delegate(Tag, ctx)


class Preprint(Parser):
    title = ctx.entry.title
    description = ctx.entry.summary
    published = tools.ParseDate(ctx.entry.published)
    contributors = tools.Map(tools.Delegate(Contributor), ctx.entry.author)
    links = tools.Map(
        tools.Delegate(ThroughLinks),
        tools.Maybe(ctx.entry, 'arxiv:doi')['#text']
    )
    subject = tools.Delegate(Tag, ctx.entry['arxiv:primary_category'])
    tags = tools.Map(tools.Delegate(ThroughTags), ctx.entry.category)
