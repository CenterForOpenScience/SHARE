import arrow

from share.normalize import ctx
from share.normalize.tools import *
from share.normalize.parsers import Parser


class Link(Parser):
    url = DOI(RunPython('get_list_element', ctx.metadata.article.front['article-meta']['article-id'], '@pub-id-type', 'doi'))

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
    name = ctx.record.metadata.article.front['article-meta']['kwd-group']['kwd']

    def get_published_date(self, list_):
        for item in list_:
            if item['@pub-type'] == 'epub':
                return str(arrow.get(int(item['year']), int(item['month']), int(item['day'])))

    def get_print_information(self):
        volume = ctx.record.metadata.article.front['article-meta']['volume']
        issue = ctx.record.metadata.article.front['article-meta']['issue']
        fpage = ctx.record.metadata.article.front['article-meta']['fpage']
        lpage = ctx.record.metadata.article.front['article-meta']['lpage']
        return "This work appeared in volume {} issue {} from pages {} - {}.".format(volume, issue, fpage, lpage)

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
        for item in list_:
            issns[item['@pub-type']] = item['#text']
        return issns


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Publication(Parser):
    title = OneOf(
        ctx.record.metadata.article.front['article-meta']['title-group']['article-title']['#text'],
        ctx.record.metadata.article.front['article-meta']['title-group']['article-title'],
    )
    description = OneOf(
        ctx.record.metadata.article.front['article-meta']['abstract']['p']['#text'],
        ctx.record.metadata.article.front['article-meta']['abstract']['p'],
        RunPython('get_abstract', ctx.record.metadata.article.front['article-meta']['abstract']),
        ctx.record.metadata.article.front['article-meta']['abstract']['sec']['p'],
    )
    # description = RunPython('get_abstract', ctx.record.metadata.article.front['article-meta']['abstract'])

    publishers = Try(Map(
        Delegate(Association.using(entity=Delegate(Publisher))),
        ctx.record.metadata.article.front['journal-meta']['publisher']['publisher-name']
    ))
    funders = Try(Map(
        Delegate(Association.using(entity=Delegate(Funder))),
        ctx.record.metadata.article.front['article-meta']['funding-group']['award-group']['funding-source']
    ))

    tags = Try(Map(Delegate(ThroughTags), ctx))

    date_published = RunPython(
        'get_published_date',
        ctx.record.metadata.article.front['article-meta']['pub-date']
    )

    links = Map(Delegate(ThroughLinks), ctx.record)

    rights = Concat(ctx.record.metadata.article.front['article-meta']['permissions']['license']['license-p'])

    contributors = Map(
        Delegate(Contributor),
        ctx.record.metadata.article.front['article-meta']['contrib-group']['contrib']
    )

    class Extra:
        correspondence = Try(ctx.record.metadata.article.front['article-meta']['author-notes']['corresp']['email'])
        journal = ctx.record.metadata.article.front['journal-meta']['journal-title-group']['journal-title']
        in_print = Try(RunPython('get_print_information'))
        issn = Try(RunPython('get_issns', ctx.record.metadata.article.front['journal-meta']['issn']))
        doi = RunPython('get_list_element', ctx.record.metadata.article.front['article-meta']['article-id'],
                        '@pub-id-type', 'doi')
        pubmed_id = Try(RunPython('get_list_element', ctx.record.metadata.article.front['article-meta']['article-id'],
                        '@pub-id-type', 'pmcid'))
        # date_received = pass
        # date_accepted = pass
        copyright = Try(OneOf(
            ctx.record.metadata.article.front['article-meta']['permissions']['copyright-statement']['#text'],
            ctx.record.metadata.article.front['article-meta']['permissions']['copyright-statement']
        ))
        copyright_year = Try(ctx.record.metadata.article.front['article-meta']['permissions']['copyright-year'])

        def get_published_date(self, list_):
            for item in list_:
                if item['@pub-type'] == 'epub':
                    return str(arrow.get(int(item['year']), int(item['month']), int(item['day'])))

    def get_abstract(self, node):
        for section in node:
            if section['title']:
                return section['p']


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
        for item in list_:
            issns[item['@pub-type']] = item['#text']
        return issns

    def get_published_date(self, list_):
        for item in list_:
            if item['@pub-type'] == 'epub':
                return str(arrow.get(int(item['year']), int(item['month']), int(item['day'])))


    def get_date(self, list_):
        pass

    def get_print_information(self):
        volume = ctx.record.metadata.article.front['article-meta']['volume']
        issue = ctx.record.metadata.article.front['article-meta']['issue']
        fpage = ctx.record.metadata.article.front['article-meta']['fpage']
        lpage = ctx.record.metadata.article.front['article-meta']['lpage']
        return "This work appeared in volume {} issue {} from pages {} - {}.".format(volume, issue, fpage, lpage)
