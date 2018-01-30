from share.transform.chain import *  # noqa


class WorkIdentifier(Parser):
    uri = IRI(ctx)


class Tag(Parser):
    name = ctx.name

    class Extra:
        id = ctx.id


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Person(Parser):
    given_name = ParseName(ctx.author_name).first
    family_name = ParseName(ctx.author_name).last


class DataSetPerson(Parser):
    schema = 'Person'

    given_name = ParseName(ctx.full_name).first
    family_name = ParseName(ctx.full_name).last
    suffix = ParseName(ctx.full_name).suffix
    additional_name = ParseName(ctx.full_name).middle

    class Extra:
        id = ctx.id


class DataSetCreator(Parser):
    schema = 'Creator'

    order_cited = ctx('index')
    cited_as = ctx.full_name
    agent = Delegate(DataSetPerson, ctx)


class Creator(Parser):
    order_cited = ctx('index')
    cited_as = ctx.author_name
    agent = Delegate(Person, ctx)


class CreativeWork(Parser):
    title = ctx.title
    description = ctx.description
    related_agents = Map(Delegate(Creator), ctx.authors)
    date_published = ParseDate(ctx.published_date)
    identifiers = Map(Delegate(WorkIdentifier), Map(Try(IRI(), exceptions=(InvalidIRI, )), ctx.url, ctx.DOI, ctx.links))

    class Extra:
        modified = ParseDate(ctx.modified_date)


class DataSet(Parser):
    schema = 'DataSet'
    title = ctx.title
    description = ctx.description_nohtml
    date_published = ParseDate(ctx.published_date)

    tags = Map(Delegate(ThroughTags), ctx.categories, ctx.tags)
    related_agents = Map(Delegate(DataSetCreator), ctx.owner, ctx.authors)
    identifiers = Map(Delegate(WorkIdentifier), ctx.figshare_url, ctx.doi, ctx.publisher_doi)

    class Extra:
        status = ctx.status
        version = ctx.version
        total_size = ctx.total_size
        article_id = ctx.article_id
        defined_type = ctx.defined_type
        citation = ctx.publisher_citation


class FigshareTransformer(ChainTransformer):
    VERSION = 1

    def get_root_parser(self, unwrapped, **kwargs):
        if 'files' in unwrapped:
            return DataSet
        return CreativeWork
