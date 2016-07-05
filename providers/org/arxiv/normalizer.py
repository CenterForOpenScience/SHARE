from share.normalize import ctx, links
from share.normalize.parsers import Parser
from share.normalize.utils import format_doi_as_url


class Link(Parser):
    url = links.RunPython('format_doi', ctx)
    # identifier will always be DOI
    type = links.Static('doi')

    def format_doi(self, doi):
        return format_doi_as_url(self, doi)


class ThroughLinks(Parser):
    link = links.Delegate(Link, ctx)


class Organization(Parser):
    name = ctx['#text']


class Affiliation(Parser):
    pass


class Person(Parser):
    given_name = links.ParseName(ctx.name).first
    family_name = links.ParseName(ctx.name).last
    additional_name = links.ParseName(ctx.name).middle
    suffix = links.ParseName(ctx.name).suffix
    affiliations = links.Map(
        links.Delegate(Affiliation.using(entity=links.Delegate(Organization))),
        links.Maybe(ctx, 'arxiv:affiliation')
    )


class Contributor(Parser):
    order_cited = ctx('index')
    cited_name = ctx.name
    person = links.Delegate(Person, ctx)


class Tag(Parser):
    name = ctx['@term']


class ThroughTags(Parser):
    tag = links.Delegate(Tag, ctx)


class Preprint(Parser):
    title = ctx.entry.title
    description = ctx.entry.summary
    published = links.ParseDate(ctx.entry.published)
    contributors = links.Map(links.Delegate(Contributor), ctx.entry.author)
    links = links.Map(
        links.Delegate(ThroughLinks),
        links.Maybe(ctx.entry['arxiv:primary_category']['#text'])
    )
    subject = links.Delegate(Tag, ctx.entry['arxiv:primary_category'])
    tags = links.Map(links.Delegate(ThroughTags), ctx.entry.category)
