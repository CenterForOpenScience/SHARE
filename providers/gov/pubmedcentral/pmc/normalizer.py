import arrow
from collections import OrderedDict

from share.normalize import ctx
from share.normalize.tools import *
from share.normalize.soup import SoupXMLNormalizer
from share.normalize.parsers import Parser

PMCID_FORMAT = 'http://www.ncbi.nlm.nih.gov/pmc/articles/PMC{}/'
PMID_FORMAT = 'http://www.ncbi.nlm.nih.gov/pubmed/{}'

def pmcid_uri(pmcid):
    if pmcid.startswith('PMC'):
        pmcid = pmcid[3:]
    return PMCID_FORMAT.format(pmcid)

def pmid_uri(pmid):
    return PMID_FORMAT.format(pmid)



class WorkIdentifier(Parser):
    uri = ctx


class AgentIdentifier(Parser):
    uri = ctx


class Organization(Parser):
    name = OneOf(ctx['#text'], ctx)


class Publisher(Parser):
    agent = Delegate(Organization, ctx)


class Person(Parser):
    suffix = Try(ctx['name']['suffix'])
    family_name = ctx['name']['surname']
    given_name = ctx['name']['given-names']

    identifiers = Map(
        Delegate(AgentIdentifier),
        Map(
            IRI(),
            Soup(ctx, 'contrib-id', **{'contrib-id-type': 'orcid'})['#text'],
            Soup(ctx, 'email')['#text']
        )
    )

    class Extra:
        role = Try(ctx['role'])
        degrees = Try(ctx['degrees'])


class Contributor(Parser):
    agent = Delegate(Person, ctx)


class ContributorOrganization(Parser):
    schema = 'Contributor'
    agent = Delegate(Organization, ctx['collab'])


class Tag(Parser):
    name = ctx['#text']


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class RelatedWork(Parser):
    schema = 'CreativeWork'

    identifiers = Map(
        Delegate(WorkIdentifier),
        RunPython('get_uri', ctx)
    )

    def get_uri(self, soup):
        # TODO check link type, format pmid/pmcid


class WorkRelation(Parser):
    schema = RunPython('get_relation_type', ctx)
    related = Delegate(RelatedWork, ctx)

    def get_relation_type(self, related):
        return {
            'retracted-article': 'Retracts',
            'corrected-article': 'Corrects',
            'commentary-article': 'Discusses',
            'commentary': 'Discusses',
            'letter': 'RepliesTo',
            'letter-reply': 'RepliesTo',
            'object-of-concern': 'Disputes',
        }.get(related['related-article-type'], 'References')


class Article(Parser):
    title = ctx.record.metadata.article.front['article-meta']['title-group']['article-title']['#text'],

    description = Try(ctx.record.metadata.article.front['article-meta']['abstract']['#text'])

    related_agents = Concat(
        Delegate(Publisher, Try(ctx.record.metadata.article.front['journal-meta']['publisher'])),
        Map(
            Delegate(Creator),
            Soup(
                ctx.record.metadata.article.front['article-meta']['contrib-group'],
                'contrib',
                **{'contrib-type': 'author'}
            )
        ),
    )

    tags = Map(
        Delegate(ThroughTags),
        Concat(Try(ctx.record.metadata.article.front['article-meta']['kwd-group']['kwd']))
    )

    date_published = RunPython(
        'get_published_date',
        ctx.record.metadata.article.front['article-meta']['pub-date']
    )

    identifiers = Concat(
        Map(
            Delegate(WorkIdentifier),
            Map(
                IRI(),
                Soup(
                    ctx.record.metadata.article.front['article-meta']
                    'article-id',
                    **{'pub-id-type': 'doi'}
                ),
                Map(
                    RunPython(pmcid_uri),
                    Soup(
                        ctx.record.metadata.article.front['article-meta']
                        'article-id',
                        **{'pub-id-type': 'pmcid'}
                    )
                ),
                Map(
                    RunPython(pmid_uri),
                    Soup(
                        ctx.record.metadata.article.front['article-meta']
                        'article-id',
                        **{'pub-id-type': 'pmid'}
                    )
                )
            )
        ),
    )

    related_works = Map(
        Delegate(WorkRelation),
        Soup('related-article', **{'ext-link-type': ['doi', 'pmid', 'pmcid'], 'xlink:href': True})
    )

    rights = Try(ctx.record.metadata.article.front['article-meta']['permissions']['license']['license-p']['#text'])

    class Extra:
        correspondence = OneOf(
            ctx.record.metadata.article.front['article-meta']['author-notes']['corresp']['email'],
            ctx.record.metadata.article.front['article-meta']['author-notes']['corresp'],
            Static(None)
        )
        journal = ctx.record.metadata.article.front['journal-meta']['journal-title-group']['journal-title']
        in_print = Try(RunPython('get_print_information', ctx.record.metadata.article.front['article-meta']))
        issn = (RunPython('get_issns', ctx.record.metadata.article.front['journal-meta']['issn']))

        copyright = OneOf(
            ctx.record.metadata.article.front['article-meta']['permissions']['copyright-statement']['#text'],
            ctx.record.metadata.article.front['article-meta']['permissions']['copyright-statement'],
            Static(None)
        )
        copyright_year = Try(ctx.record.metadata.article.front['article-meta']['permissions']['copyright-year'])
        epub_date = RunPython('get_year_month_day', ctx.record.metadata.article.front['article-meta']['pub-date'], 'epub')
        ppub_date = RunPython('get_year_month_day', ctx.record.metadata.article.front['article-meta']['pub-date'], 'ppub')

    def get_issns(self, list_):
        issns = {}
        if isinstance(list_, OrderedDict):
            issns[list_['@pub-type']] = list_['#text']
        else:
            for item in list_:
                issns[item['@pub-type']] = item['#text']
        return issns

    def get_published_date(self, list_):
        # There is only one result for a published date:
        if isinstance(list_, OrderedDict):
            if list_['@pub-type'] == 'epub':
                year = list_.get('year')
                month = list_.get('month')
                day = list_.get('day')
                if year and month and day:
                    return str(arrow.get(int(year), int(month), int(day)))
        # There is an electronic and print publishing date:
        else:
            for item in list_:
                if item['@pub-type'] == 'epub':
                    year = item.get('year')
                    month = item.get('month')
                    day = item.get('day')
                    if year and month and day:
                        return str(arrow.get(int(year), int(month), int(day)))

    def get_year_month_day(self, list_, pub):
        # There is only one result for a published date:
        if isinstance(list_, OrderedDict):
            if list_['@pub-type'] == pub:
                year = list_.get('year')
                month = list_.get('month')
                day = list_.get('day')
                return year, month, day
        # There is an electronic and print publishing date:
        else:
            for item in list_:
                if item['@pub-type'] == pub:
                    year = item.get('year')
                    month = item.get('month')
                    day = item.get('day')
                    return year, month, day

    def get_print_information(self, ctx):
        volume = ctx['volume']
        issue = ctx['issue']
        fpage = ctx['fpage']
        lpage = ctx['lpage']
        return "This work appeared in volume {} issue {} from pages {} - {}.".format(volume, issue, fpage, lpage)


class PMCNormalizer(SoupXMLNormalizer):
    # TODO retractions with no related works should be CreativeWorks with a related (nearly empty) retraction?

    def unwrap_data(self, data):
        soup = super().unwrap_data(data)
        self.resolve_xrefs(soup)
        return soup

    def resolve_xrefs(self, soup):
        for xref in soup.find_all('xref', ref-type=True, rid=True):
            resolved = soup.find(xref['ref-type'], id=xref['rid'])
            if not resolved:
                continue
            if xref.string:
                label = resolved.find(string=xref.string)
                if label:
                    label.extract()
            xref.replace_with(resolved.copy())
