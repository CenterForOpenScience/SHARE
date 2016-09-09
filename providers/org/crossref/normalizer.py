import furl

from share.normalize import *
from share.normalize import links


class Publisher(Parser):
    name = ctx


class Funder(Parser):
    name = ctx.name

    class Extra:
        doi = Maybe(ctx, 'DOI')
        award = Maybe(ctx, 'award')
        doi_asserted_by = Maybe(ctx, 'doi-asserted-by')


class Association(Parser):
    pass


class Organization(Parser):
    name = Maybe(ctx, 'name')


class Affiliation(Parser):
    pass


class Identifier(Parser):
    url = ctx
    domain = RunPython('get_domain', ctx)

    def get_domain(self, url):
        return furl.furl(url).host


class PersonIdentifier(Parser):
    identifier = Delegate(Identifier, Orcid(ctx))


class WorkIdentifier(Parser):
    identifier = Delegate(Identifier, DOI(ctx))


class Person(Parser):
    given_name = Maybe(ctx, 'given')
    family_name = Maybe(ctx, 'family')
    affiliations = Map(Delegate(Affiliation.using(entity=Delegate(Organization))), Maybe(ctx, 'affiliation'))
    personidentifiers = Map(Delegate(PersonIdentifier), Maybe(ctx, 'ORCID'))


class WorkIdentifier(Parser):
    url = RunPython('format_doi_as_url', ctx)

    def format_doi_as_url(self, doi):
        return format_doi_as_url(self, doi)

class Contributor(Parser):
    person = Delegate(Person, ctx)
    order_cited = ctx('index')
    cited_name = links.Join(
        Concat(
            Maybe(ctx, 'given'),
            Maybe(ctx, 'family')
        ),
        joiner=' '
    )


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class CreativeWork(Parser):
    """
    Documentation for CrossRef's metadata can be found here:
    https://github.com/CrossRef/rest-api-doc/blob/master/api_format.md
    """

    title = Maybe(ctx, 'title')[0]
    description = Maybe(ctx, 'subtitle')[0]
    date_updated = ParseDate(Try(ctx.deposited['date-time']))

    contributors = Map(
        Delegate(Contributor),
        Maybe(ctx, 'author')
    )

    identifiers = Map(Delegate(WorkIdentifier), ctx.DOI)

    publishers = Map(
        Delegate(Association.using(entity=Delegate(Publisher))),
        ctx.publisher
    )
    funders = Map(
        Delegate(Association.using(entity=Delegate(Funder))),
        Maybe(ctx, 'funder')
    )
    # TODO These are "a controlled vocabulary from Sci-Val", map to Subjects!
    tags = Map(
        Delegate(ThroughTags),
        Maybe(ctx, 'subject')
    )


    class Extra:
        alternative_id = Maybe(ctx, 'alternative-id')
        archive = Maybe(ctx, 'archive')
        article_number = Maybe(ctx, 'article-number')
        chair = Maybe(ctx, 'chair')
        container_title = Maybe(ctx, 'container-title')
        date_created = ParseDate(Try(ctx.created['date-time']))
        date_published = Maybe(ctx, 'issued')
        editor = Maybe(ctx, 'editor')
        licenses = Maybe(ctx, 'license')
        isbn = Maybe(ctx, 'isbn')
        issn = Maybe(ctx, 'issn')
        issue = Maybe(ctx, 'issue')
        member = Maybe(ctx, 'member')
        page = Maybe(ctx, 'page')
        published_online = Maybe(ctx, 'published-online')
        published_print = Maybe(ctx, 'published-print')
        reference_count = ctx['reference-count']
        subjects = Maybe(ctx, 'subject')
        subtitles = Maybe(ctx, 'subtitle')
        titles = ctx.title
        translator = Maybe(ctx, 'translator')
        type = ctx.type
        volume = Maybe(ctx, 'volume')


class Article(CreativeWork):
    pass


class Book(CreativeWork):
    pass


class ConferencePaper(CreativeWork):
    pass


class Dataset(CreativeWork):
    pass


class Dissertation(CreativeWork):
    pass


class Preprint(CreativeWork):
    pass


class Report(CreativeWork):
    pass


class Section(CreativeWork):
    pass


class CrossRefNormalizer(Normalizer):
    def do_normalize(self, data):
        unwrapped = self.unwrap_data(data)

        parser = {
            'journal-article': Article,
            'book': Book,
            'proceedings-article': ConferencePaper,
            'dataset': Dataset,
            'dissertation': Dissertation,
            'preprint': Preprint,
            'report': Report,
            'book-section': Section,
        }.get(unwrapped['type']) or CreativeWork

        return parser(unwrapped).parse()
