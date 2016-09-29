import arrow

from share.normalize import ctx
from share.normalize.tools import *
from share.normalize.parsers import Parser


class Link(Parser):
    Schema = 'Link'
    url = DOI(XPath(ctx.record.metadata.article.front['article-meta']['article-id'], "str[@pub-id-type='doi']"))
    # url = DOI(RunPython('get_list_element', ctx.record.metadata.article.front['article-meta']['article-id'],
    #                     '@pub-id-type', 'doi'))


class ThroughLinks(Parser):
    Schema = 'ThroughLinks'
    link = Delegate(Link, ctx)


class Affiliation(Parser):
    pass


class Institution(Parser):
    schema = 'Institution'
    name = ctx


class Person(Parser):
    suffix = Try(ctx['name']['suffix'])
    family_name = ctx['name']['surname']
    given_name = ctx['name']['given-names']


class Contributor(Parser):
    person = Delegate(Person, ctx)
    # order_cited = ctx('index')
    cited_name = ctx['name']['surname']


class Publisher(Parser):
    name = ctx


class Funder(Parser):
    name = ctx


class Association(Parser):
    entity = Delegate(Publisher, ctx)


class Tag(Parser):
    name = ctx.record.metadata.article.front['article-meta']['kwd-group']['kwd']


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class Publication(Parser):
    title = ctx.record.metadata.article.front['article-meta']['title-group']['article-title']
    description = OneOf(
        ctx.record.metadata.article.front['article-meta']['abstract']['p'],
        ctx.record.metadata.article.front['article-meta']['abstract']['sec'][1]['p']
    )

    publishers = Map(
        Delegate(Association.using(entity=Delegate(Publisher))),
        ctx.record.metadata.article.front['journal-meta']['publisher']['publisher-name']
    )
    funders = Try(Map(
        Delegate(Association.using(entity=Delegate(Funder))),
        ctx.record.metadata.article.front['article-meta']['funding-group']['award-group']['funding-source']
    ))

    tags = Try(Map(Delegate(ThroughTags), ctx))

    # date_published = RunPython('get_published_date', ctx.record.metadata.article.front['article-meta']['pub-date'])
    # date_published = Concat(XPath(ctx.record.metadata.article.front['article-meta']['pub-date'], "str[@pub-type='epub']"))

    # links = Map(Delegate(ThroughLinks), ctx)

    rights = Concat(ctx.record.metadata.article.front['article-meta']['permissions']['license']['license-p'])

    contributors = Map(Delegate(Contributor), ctx.record.metadata.article.front['article-meta']['contrib-group']['contrib'])

    # institutions = Map()

    # institutions
    # funding


    # contributors = Map(
    #     Delegate(Contributor),
    #     front['article-meta']['contrib-group']['contrib']
    # )

    # description = Join(RunPython('force_text', Try(ctx.record.metadata.dc['dc:description'])))
    #
    # publishers = Map(
    #     Delegate(OAIAssociation.using(entity=Delegate(OAIPublisher))),
    #     Map(RunPython('force_text'), Try(ctx.record.metadata.dc['dc:publisher']))
    # )
    #
    # rights = Join(Maybe(Maybe(ctx['record'], 'metadata')['dc'], 'dc:rights'))
    #
    # # Note: this is only taking the first language in the case of multiple languages
    # language = ParseLanguage(
    #     Try(ctx['record']['metadata']['dc']['dc:language'][0]),
    # )
    #
    # contributors = Map(
    #     Delegate(OAIContributor),
    #     RunPython(
    #         'get_contributors',
    #         Concat(
    #             Maybe(Maybe(ctx['record'], 'metadata')['dc'], 'dc:creator'),
    #             Maybe(Maybe(ctx['record'], 'metadata')['dc'], 'dc:contributor')
    #         ),
    #         'contributor'
    #     )
    # )
    #
    # institutions = Map(
    #     Delegate(OAIAssociation.using(entity=Delegate(OAIInstitution))),
    #     RunPython(
    #         'get_contributors',
    #         Concat(
    #             Maybe(Maybe(ctx['record'], 'metadata')['dc'], 'dc:creator'),
    #             Maybe(Maybe(ctx['record'], 'metadata')['dc'], 'dc:contributor')
    #         ),
    #         'institution'
    #     )
    # )
    #
    # organizations = Map(
    #     Delegate(OAIAssociation.using(entity=Delegate(OAIOrganization))),
    #     RunPython(
    #         'get_contributors',
    #         Concat(
    #             Maybe(Maybe(ctx['record'], 'metadata')['dc'], 'dc:creator'),
    #             Maybe(Maybe(ctx['record'], 'metadata')['dc'], 'dc:contributor')
    #         ),
    #         'organization'
    #     )
    # )

    class Extra:
        correspondence = Try(ctx.record.metadata.article.front['article-meta']['author-notes']['corresp']['email'])
        journal = ctx.record.metadata.article.front['journal-meta']['journal-title-group']['journal-title']
        in_print = Try(RunPython('get_print_information'))
        issn = Try(RunPython('get_issns', ctx.record.metadata.article.front['journal-meta']['issn']))
        doi = RunPython('get_list_element', ctx.record.metadata.article.front['article-meta']['article-id'],
                        '@pub-id-type', 'doi')
        # doi = XPath(ctx.record.metadata.article.front['article-meta']['article-id']['#text'], "str[@pub-id-type='doi']")
        pubmed_id = Try(RunPython('get_list_element', ctx.record.metadata.article.front['article-meta']['article-id'],
                        '@pub-id-type', 'pmcid'))
        # pubmed_id = XPath(ctx.record.metadata.article.front['article-meta']['article-id'], "str[@pub-id-type='pmcid']")
        copyright = ctx.record.metadata.article.front['article-meta']['permissions']['copyright-statement']['#text']
        copyright_year = ctx.record.metadata.article.front['article-meta']['permissions']['copyright-year']

        def get_published_date(self, list_):
            for item in list_:
                if item['@pub-type'] == 'epub':
                    return str(arrow.get(int(item['year']), int(item['month']), int(item['day'])))

    # def compose_name(self, suffix, surname, given):
    #     return ' '.join([given, surname, suffix])

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

    def get_print_information(self):
        volume = ctx.record.metadata.article.front['article-meta']['volume']
        issue = ctx.record.metadata.article.front['article-meta']['issue']
        fpage = ctx.record.metadata.article.front['article-meta']['fpage']
        lpage = ctx.record.metadata.article.front['article-meta']['lpage']
        return "This work appeared in volume {} issue {} from pages {} - {}.".format(volume, issue, fpage, lpage)
