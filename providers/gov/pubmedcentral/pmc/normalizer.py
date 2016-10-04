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


class Contributor(Parser):
    person = Delegate(Person, ctx)
    cited_name = ctx['name']['surname']


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

    publishers = Try(Map(
        Delegate(Association.using(entity=Delegate(Publisher))),
        ctx.record.metadata.article.front['journal-meta']['publisher']['publisher-name']
    ))
    funders = Try(Map(
        Delegate(Association.using(entity=Delegate(Funder))),
        ctx.record.metadata.article.front['article-meta']['funding-group']['award-group']['funding-source']
    ))

    tags = Try(Map(Delegate(ThroughTags), ctx.record.metadata.article.front['article-meta']['kwd-group']['kwd']))

    date_published = RunPython(
        'get_published_date',
        ctx.record.metadata.article.front['article-meta']['pub-date']
    )

    links = Map(Delegate(ThroughLinks), ctx.record)

    rights = Try(ctx.record.metadata.article.front['article-meta']['permissions']['license']['license-p']['#text'])

    contributors = Try(Map(
        Delegate(Contributor),
        ctx.record.metadata.article.front['article-meta']['contrib-group']['contrib']
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
        epub_date = RunPython('get_year_month_day', ctx.record.metadata.article.front['article-meta']['pub-date'], 'epub')
        ppub_date = RunPython('get_year_month_day', ctx.record.metadata.article.front['article-meta']['pub-date'], 'ppub')

    def extract_abstract(self, *args):
        for i in range(len(args)):
            try:
                arg = args[i]
                if isinstance(arg, str) or arg is None:
                    return arg
            except:
                continue

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

    def get_name(self, person):
        given_name = person['given_names']
        surname = person['surname']
        suffix = Try(person['suffix'])
        print(given_name + ' ' + surname + ' ' + suffix)
        return given_name + ' ' + surname + ' ' + suffix

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
