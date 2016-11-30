import arrow
from collections import OrderedDict

from share.normalize import ctx
from share.normalize.tools import *
from share.normalize.parsers import Parser


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

    identifiers = Map(Delegate(AgentIdentifier), Map(IRI(), Try(RunPython(
        'get_list_element', Concat(ctx['contrib-id']), '@contrib-id-type', 'orcid')
    )))

    class Extra:
        email = OneOf(
            ctx['email'],
            ctx['address']['email'],
            Static(None)
        )
        role = Try(ctx['role'])
        degrees = Try(ctx['degrees'])

    def get_list_element(self, lst, attribute='', value=''):
        for ordered_dict in lst:
            if ordered_dict[attribute] == value:
                return ordered_dict['#text']


class Contributor(Parser):
    agent = Delegate(Person, ctx)


class ContributorOrganization(Parser):
    schema = 'Contributor'
    agent = Delegate(Organization, ctx['collab'])


class Tag(Parser):
    name = OneOf(
        ctx['#text'],
        ctx['italic'],
        ctx['styled-content']['#text'],
        ctx['styled-content']['italic'],
        ctx
    )


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Article(Parser):
    title = OneOf(
        ctx.record.metadata.article.front['article-meta']['title-group']['article-title']['#text'],
        ctx.record.metadata.article.front['article-meta']['title-group']['article-title'],
    )
    description = OneOf(
        Try(ctx.record.metadata.article.front['article-meta']['abstract'][0]['p']['#text']),
        Try(ctx.record.metadata.article.front['article-meta']['abstract'][1]['p']['#text']),
        ctx.record.metadata.article.front['article-meta']['abstract'][0]['p'],
        ctx.record.metadata.article.front['article-meta']['abstract'][1]['p'],
        ctx.record.metadata.article.front['article-meta']['abstract']['p']['#text'],
        ctx.record.metadata.article.front['article-meta']['abstract']['p'],
        ctx.record.metadata.article.front['article-meta']['abstract']['sec'][0]['p']['#text'],
        ctx.record.metadata.article.front['article-meta']['abstract']['sec'][0]['p'],  # never seen
        ctx.record.metadata.article.front['article-meta']['abstract']['sec'][0],  # never seen
        ctx.record.metadata.article.front['article-meta']['abstract']['sec']['p'],
        Static(None)
    )

    related_agents = Concat(
        Delegate(Publisher,
                 Try(ctx.record.metadata.article.front['journal-meta']['publisher']['publisher-name'])
                 ),
        Map(Delegate(Contributor),
            RunPython(
                'get_contributors',
                Concat(Try(ctx.record.metadata.article.front['article-meta']['contrib-group']['contrib'])),
                'person')),
        Map(Delegate(ContributorOrganization),
            RunPython(
                'get_contributors',
                Concat(Try(ctx.record.metadata.article.front['article-meta']['contrib-group']['contrib'])),
                'organization')))

    tags = Map(
        Delegate(ThroughTags),
        Concat(Try(ctx.record.metadata.article.front['article-meta']['kwd-group']['kwd']))
    )

    date_published = RunPython(
        'get_published_date',
        ctx.record.metadata.article.front['article-meta']['pub-date']
    )

    identifiers = Map(
        Delegate(WorkIdentifier), Map(IRI(), Try(RunPython(
            'get_identifier',
            Concat(ctx.record.metadata.article.front['article-meta']['article-id']), '@pub-id-type', 'doi'))))

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
        doi = RunPython('get_list_element', ctx.record.metadata.article.front['article-meta']['article-id'],
                        '@pub-id-type', 'doi')
        pubmed_id = (RunPython('get_list_element', ctx.record.metadata.article.front['article-meta']['article-id'],
                               '@pub-id-type', 'pmcid'))

        copyright = OneOf(
            ctx.record.metadata.article.front['article-meta']['permissions']['copyright-statement']['#text'],
            ctx.record.metadata.article.front['article-meta']['permissions']['copyright-statement'],
            Static(None)
        )
        copyright_year = Try(ctx.record.metadata.article.front['article-meta']['permissions']['copyright-year'])
        epub_date = RunPython('get_year_month_day', ctx.record.metadata.article.front['article-meta']['pub-date'], 'epub')
        ppub_date = RunPython('get_year_month_day', ctx.record.metadata.article.front['article-meta']['pub-date'], 'ppub')

    def get_identifier(self, lst, attribute='', value=''):
        for ordered_dict in lst:
            if ordered_dict[attribute] == value:
                return ordered_dict['#text']

    def get_contributors(self, ctx, type):
        results = []
        if type == 'person':
            for contributor in ctx:
                if 'name' in contributor:
                    results.append(contributor)

        if type == 'organization':
            for contributor in ctx:
                if 'collab' in contributor:
                    results.append(contributor)
        return results

    # For ordered dicts
    def get_list_element(self, ordered_dict, attribute='', value=''):
        if attribute:
            for item in ordered_dict:
                if item[attribute] == value:
                    return item['#text']
        else:
            results = []
            for item in ordered_dict:
                results.append(item['#text'])
            return results

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
