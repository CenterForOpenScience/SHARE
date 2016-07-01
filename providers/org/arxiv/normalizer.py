from share.normalize import *  # noqa


class Person(Parser):
    given_name = ParseName(ctx.name).first
    family_name = ParseName(ctx.name).last
    additional_name = ParseName(ctx.name).middle
    suffix = ParseName(ctx.name).suffix
    affiliations = ctx.maybe('arxiv:affiliation')['*']


class Contributor(Parser):
    order_cited = ctx['index']
    person = ctx
    cited_name = ctx.name


class CreativeWork(Parser):
    title = ctx.entry.title
    description = ctx.entry.summary
    contributors = ctx.entry.author['*']
    published = ctx.entry.published
    doi = ctx.entry.maybe('arxiv:doi')('#text')
    subject = ctx.entry('arxiv:primary_category')
    tags = ctx.entry.category['*']


class Affiliation(Parser):
    organization = ctx


class Organization(Parser):
    name = ctx('#text')


class Tag(Parser):
    name = ctx('@term')
    type = ctx('@term')


class ThroughTags(Parser):
    tag = ctx


class Taxonomy(Parser):
    name = ctx
