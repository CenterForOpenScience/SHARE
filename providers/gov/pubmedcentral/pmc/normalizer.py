import arrow
from collections import OrderedDict

from share.normalize import ctx
from share.normalize.tools import *
from share.normalize.parsers import Parser


class Link(Parser):
    url = Try(DOI(RunPython('get_list_element', ctx.metadata.article.front['article-meta']['article-id'], '@pub-id-type', 'doi')))

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


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Affiliation(Parser):
    pass


class Person(Parser):
    suffix = Try(ctx['name']['suffix'])
    family_name = ctx['name']['surname']
    given_name = ctx['name']['given-names']

    class Extra:
        email = OneOf(
            ctx['email'],
            ctx['address']['email'],
            Static(None)
        )
        contrib_id = Try(Orcid(ctx['contrib-id']))
        role = Try(ctx['role'])
        degrees = Try(ctx['degrees'])


class Contributor(Parser):
    person = Delegate(Person, ctx)
    cited_name = ctx['name']['surname']


class ContributorOrganization(Parser):
    schema = 'Organization'
    name = OneOf(
        ctx['collab']['#text'],
        ctx['collab']
    )


class Publisher(Parser):
    name = ctx


class Funder(Parser):
    name = ctx


class Association(Parser):
    entity = Delegate(Publisher, ctx)


class Tag(Parser):
    name = OneOf(ctx['#text'], ctx['italic'], ctx)


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Publication(Parser):
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

    publishers = Map(
            Delegate(Association.using(entity=Delegate(Publisher))),
            Concat(Try(ctx.record.metadata.article.front['journal-meta']['publisher']['publisher-name']))
        )
    funders = Map(
            Delegate(Association.using(entity=Delegate(Funder))),
            Concat(Try(ctx.record.metadata.article.front['article-meta']['funding-group']['award-group']['funding-source']))
        )

    tags = Map(
        Delegate(ThroughTags),
        Concat(Try(ctx.record.metadata.article.front['article-meta']['kwd-group']['kwd']))
    )

    date_published = RunPython(
        'get_published_date',
        ctx.record.metadata.article.front['article-meta']['pub-date']
    )

    links = Map(Delegate(ThroughLinks), ctx.record)

    rights = Try(ctx.record.metadata.article.front['article-meta']['permissions']['license']['license-p']['#text'])

    contributors = Concat(Map(
        Delegate(Contributor),
        RunPython(
            'get_contributors',
            Concat(Try(ctx.record.metadata.article.front['article-meta']['contrib-group']['contrib'])),
            'person'
        )),
        Map(
            Delegate(Association.using(entity=Delegate(ContributorOrganization))),
            RunPython(
                'get_contributors',
                Concat(Try(ctx.record.metadata.article.front['article-meta']['contrib-group']['contrib'])),
                'organization'
            )
        ))

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

    def get_contributors(self, ctx, type):
        results = []

        if type == 'person':
            for contributor in ctx:
                try:
                    contributor['name']
                    results.append(contributor)
                except:
                    pass
        if type == 'organization':
            for contributor in ctx:
                try:
                    contributor['collab']
                    results.append(contributor)
                except:
                    pass
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
        if type(list_) == OrderedDict:
            issns[list_['@pub-type']] = list_['#text']
        else:
            for item in list_:
                issns[item['@pub-type']] = item['#text']
        return issns

    def get_published_date(self, list_):
        # There is only one result for a published date:
        if type(list_) == OrderedDict:
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
        if type(list_) == OrderedDict:
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
