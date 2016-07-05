from django.conf import settings

from share.normalize import *  # noqa


class Organization(Parser):
    name = ctx['#text']


class Affiliation(Parser):
    pass


class Person(Parser):
    given_name = ParseName(ctx.name).first
    family_name = ParseName(ctx.name).last
    additional_name = ParseName(ctx.name).middle
    suffix = ParseName(ctx.name).suffix
    affiliations = Map(
        Delegate(Affiliation.using(entity=Delegate(Organization))),
        Maybe(ctx, 'arxiv:affiliation')
    )


class Contributor(Parser):
    order_cited = ctx('index')
    cited_name = ctx.name
    person = Delegate(Person, ctx)


class Tag(Parser):
    name = ctx['@term']


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Preprint(Parser):
    title = ctx.entry.title
    description = ctx.entry.summary
    published = ParseDate(ctx.entry.published)
    contributors = Map(Delegate(Contributor), ctx.entry.author)
    # doi = settings.DOI_BASE_URL + ctx.entry.maybe('arxiv:doi')['#text']
    subject = Delegate(Tag, ctx.entry['arxiv:primary_category'])
    tags = Map(Delegate(ThroughTags), ctx.entry.category)
