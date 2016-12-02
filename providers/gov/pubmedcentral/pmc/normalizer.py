import arrow
from collections import OrderedDict

from share.normalize import ctx
from share.normalize.tools import *
from share.normalize.soup import SoupXMLNormalizer, SoupXMLDict, Soup
from share.normalize.parsers import Parser

PMCID_FORMAT = 'http://www.ncbi.nlm.nih.gov/pmc/articles/PMC{}/'
PMID_FORMAT = 'http://www.ncbi.nlm.nih.gov/pubmed/{}'

def pmcid_uri(pmcid):
    if isinstance(pmcid, SoupXMLDict):
        pmcid = pmcid['#text']
    if pmcid.startswith('PMC'):
        pmcid = pmcid[3:]
    return PMCID_FORMAT.format(pmcid)


def pmid_uri(pmid):
    if isinstance(pmid, SoupXMLDict):
        pmid = pmid['#text']
    return PMID_FORMAT.format(pmid)


class WorkIdentifier(Parser):
    uri = ctx


class AgentIdentifier(Parser):
    uri = ctx


class PublisherOrganization(Parser):
    schema = GuessAgentType(ctx['publisher-name']['#text'], 'organization')
    name = ctx['publisher-name']['#text']
    location = ctx['publisher-loc']['#text']


class Publisher(Parser):
    agent = Delegate(PublisherOrganization, ctx)


class JournalOrganization(Parser):
    schema = 'organization'
    name = ctx['journal-title-group']['journal-title']['#text']
    identifiers = Map(
        Delegate(AgentIdentifier),
        Map(
            IRI(),
            RunPython('get_issns', ctx)
        )
    )

    def get_issns(self, obj):
        return [t['#text'] for t in obj['issn']]


class Journal(Parser):
    schema = 'publisher'
    agent = Delegate(JournalOrganization, ctx)


class Person(Parser):
    suffix = Try(ctx.name.suffix['#text'])
    family_name = ctx.name.surname['#text']
    given_name = Try(ctx.name['given-names']['#text'])

    identifiers = Map(
        Delegate(AgentIdentifier),
        Map(
            IRI(),
            Try(Soup(ctx, 'contrib-id', **{'contrib-id-type': 'orcid'})['#text']),
            Try(Soup(ctx, 'email')['#text'])
        )
    )

    # TODO affiliations

    class Extra:
        role = Try(ctx.role['#text'])
        degrees = Try(ctx.degrees['#text'])


class Consortium(Parser):
    name = ctx


class Creator(Parser):
    agent = Delegate(Person, ctx)
    order_cited = ctx('index')

    cited_as = RunPython('get_cited_as', ctx.name)

    def get_cited_as(self, obj):
        surname = obj.soup.surname
        given = obj.soup.find('given-names')
        if given:
            return '{}, {}'.format(surname.get_text(), given.get_text())
        return surname.get_text()


class CollabCreator(Parser):
    schema = 'creator'
    agent = Delegate(Consortium, RunPython('collab_name', ctx))

    def collab_name(self, obj):
        nested_group = obj.soup.find('contrib-group')
        if nested_group:
            # TODO add ThroughContributors
            nested_group.extract()
        return obj['#text']


class Tag(Parser):
    name = ctx['#text']


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class RelatedWork(Parser):
    schema = 'creativework'

    identifiers = Map(
        Delegate(WorkIdentifier),
        IRI(RunPython('get_uri', ctx))
    )

    def get_uri(self, soup):
        id = soup['@xlink:href']
        id_type = soup['@ext-link-type']
        if id_type == 'pmid':
            return pmid_uri(id)
        if id_type == 'pmcid':
            return pmcid_uri(id)
        return id


class WorkRelation(Parser):
    schema = RunPython('get_relation_type', ctx)
    related = Delegate(RelatedWork, ctx)

    def get_relation_type(self, related):
        return {
            'retracted-article': 'retracts',
            'corrected-article': 'corrects',
            'commentary-article': 'discusses',
            'commentary': 'discusses',
            'letter': 'repliesto',
            'letter-reply': 'repliesto',
            'object-of-concern': 'disputes',
        }.get(related['@related-article-type'], 'references')


# Guidelines (largely unenforced):
# https://www.ncbi.nlm.nih.gov/pmc/pub/filespec-xml/
# https://www.ncbi.nlm.nih.gov/pmc/pmcdoc/tagging-guidelines/article/style.html
class Article(Parser):
    schema = OneOf(
        RunPython('get_schema', ctx.record.metadata.article['@article-type']),
        Static('publication')
    )

    title = ctx.record.metadata.article.front['article-meta']['title-group']['article-title']['#text']

    description = Try(ctx.record.metadata.article.front['article-meta']['abstract']['#text'])

    related_agents = Concat(
        Try(Delegate(Journal, ctx.record.metadata.article.front['journal-meta'])),
        Try(Delegate(Publisher, ctx.record.metadata.article.front['journal-meta']['publisher'])),
        Map(
            Delegate(Creator),
            Soup(
                ctx.record.metadata.article.front['article-meta']['contrib-group'],
                lambda tag: tag.name == 'contrib' and tag['contrib-type'] == 'author' and tag('name', recursive=False)
            )
        ),
        Map(
            Delegate(CollabCreator),
            Soup(
                ctx.record.metadata.article.front['article-meta']['contrib-group'],
                lambda tag: tag.name == 'contrib' and tag['contrib-type'] == 'author' and tag.collab
            )
        ),
    )

    tags = Map(
        Delegate(ThroughTags),
        Concat(Try(ctx.record.metadata.article.front['article-meta']['kwd-group']['kwd']))
    )

    date_published = RunPython(
        'get_date_published',
        ctx.record.metadata.article.front['article-meta'],
        ['epub', 'ppub', 'epub-ppub', 'epreprint', 'collection', 'pub']
    )

    identifiers = Concat(
        Map(
            Delegate(WorkIdentifier),
            Map(
                IRI(),
                Try(Soup(
                    ctx.record.metadata.article.front['article-meta'],
                    'article-id',
                    **{'pub-id-type': 'doi'}
                )['#text']),
                Map(
                    RunPython(pmcid_uri),
                    Soup(
                        ctx.record.metadata.article.front['article-meta'],
                        'article-id',
                        **{'pub-id-type': 'pmcid'}
                    )
                ),
                Map(
                    RunPython(pmid_uri),
                    Soup(
                        ctx.record.metadata.article.front['article-meta'],
                        'article-id',
                        **{'pub-id-type': 'pmid'}
                    )
                )
            )
        ),
    )

    related_works = Concat(
        Map(
            Try(Delegate(WorkRelation)),
            Soup(ctx, 'related-article', **{'ext-link-type': ['doi', 'pmid', 'pmcid'], 'xlink:href': True})
        )
    )

    rights = Try(ctx.record.metadata.article.front['article-meta']['permissions']['license']['license-p']['#text'])

    class Extra:
        correspondence = Try(ctx.record.metadata.article.front['article-meta']['author-notes']['corresp']['email']['#text'])
        journal = ctx.record.metadata.article.front['journal-meta']['journal-title-group']['journal-title']['#text']
        in_print = Try(RunPython('get_print_information', ctx.record.metadata.article.front['article-meta']))

        copyright = Try(ctx.record.metadata.article.front['article-meta']['permissions']['copyright-statement']['#text'])
        copyright_year = Try(ctx.record.metadata.article.front['article-meta']['permissions']['copyright-year']['#text'])
        epub_date = RunPython(
            'get_year_month_day',
            Soup(ctx.record.metadata.article.front['article-meta'], 'pub-date', **{'pub-type': 'epub'})
        )
        ppub_date = RunPython(
            'get_year_month_day',
            Soup(ctx.record.metadata.article.front['article-meta'], 'pub-date', **{'pub-type': 'ppub'})
        )

    def get_schema(self, article_type):
        return {
            # 'abstract'
            # 'addendum'
            # 'announcement'
            # 'article-commentary'
            # 'book-review'
            # 'books-received'
            'brief-report': 'report',
            # 'calendar'
            'case-report': 'report',
            # 'correction'
            'data-paper': 'dataset',
            # 'discussion'
            # 'editorial'
            # 'expression-of-concern'
            # 'in-brief'
            # 'introduciton'
            # 'letter'
            'meeting-report': 'report',
            # 'methods-article'
            # 'news'
            # 'obituary'
            'oration': 'presentation',
            # 'other'
            # 'product-review'
            # 'reply'
            'research-article': 'article',
            'retraction': 'retraction',
            'review-article': 'article',
            # 'systematic-review'
        }.get(article_type, 'publication')

    def get_date_published(self, obj, types, type_attr='pub-type'):
        for t in types:
            pub_date = obj.soup.find('pub-date', **{type_attr: t})
            if pub_date:
                year = pub_date.year
                month = pub_date.month
                day = pub_date.day
                if year and month and day:
                    return str(arrow.get(int(year.string), int(month.string), int(day.string)))
        if type_attr == 'pub-type':
            return self.get_date_published(obj, types, 'date-type')
        return None

    def get_year_month_day(self, list_):
        if not list_:
            return None
        if not isinstance(list_, list):
            list_ = [list_]
        for item in list_:
            year = item['year']
            month = item['month']
            day = item['day']
            if year and month and day:
                return year['#text'], month['#text'], day['#text']
        return None

    def get_print_information(self, ctx):
        volume = ctx['volume']['#text']
        issue = ctx['issue']['#text']
        fpage = ctx['fpage']['#text']
        lpage = ctx['lpage']['#text']
        return "This work appeared in volume {} issue {} from pages {} - {}.".format(volume, issue, fpage, lpage)


class PMCNormalizer(SoupXMLNormalizer):
    # TODO retractions with no related works should be CreativeWorks with a related (nearly empty) retraction?

    def unwrap_data(self, data):
        unwrapped = super().unwrap_data(data)
        # TODO resolve only xrefs that are helpful, like affiliations
        # self.resolve_xrefs(unwrapped.soup)
        return unwrapped

    def resolve_xrefs(self, soup):
        for xref in soup.find_all('xref', **{'ref-type': True, 'rid': True}):
            resolved = soup.find(xref['ref-type'], id=xref['rid'])
            if not resolved:
                continue
            if xref.string:
                label = resolved.find(string=xref.string)
                if label:
                    label.extract()
            xref.replace_with(resolved.copy())
