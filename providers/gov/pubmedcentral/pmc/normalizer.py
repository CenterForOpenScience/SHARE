import arrow

from share.normalize import ctx
from share.normalize.tools import *
from share.normalize.parsers import Parser


class Affiliation(Parser):
    pass


class Identifier(Parser):
    base_url = Try(ctx['@schemeURI'])
    url = Join(Concat(Try(ctx['@schemeURI']), Try(ctx['#text'])), joiner='/')


class ThroughIdentifiers(Parser):
    identifier = Delegate(Identifier, ctx)


class ThroughContributor(Parser):
    schema = 'Person'

    name = ctx.record.metadata.article.front['article-meta']['contrib-group']['contrib']

    suffix = name['suffix']
    family_name = name['surname']
    given_name = name['given-names']


class Person(Parser):
    # front['article-meta']['contrib-group']['contrib'][1]['name']['surname']
    name = ctx.record.metadata.article.front['article-meta']['contrib-group']['contrib']

    suffix = ctx['suffix']
    family_name = ctx['surname']
    given_name = ctx['given-names']


class Contributor(Parser):

    person = Delegate(Person, ctx)


class ContributorInstitution(Parser):
    schema = 'Institution'

    name = ctx

    # class Extra:
    #     contributor_type = Try(ctx.contributorType)


class Publisher(Parser):
    name = ctx


class Association(Parser):
    pass


class Tag(Parser):
    name = ctx


class ThroughTags(Parser):
    tag = Delegate(Tag, ctx)


class CreativeWork(Parser):
    title = ctx.record.metadata.article.front['article-meta']['title-group']['article-title']
    description = ctx.record.metadata.article.front['article-meta']['abstract']['p']
    # Journal title
    # Publisher
    # pubmed id
    # doi
    # contributors - surname, given name, institution, contrib type

    date_published = RunPython('get_date', ctx.record.metadata.article.front['article-meta']['pub-date'])

    # volume, issue, fpage, lpage
    # accepted date
    # copyright, copyright year
    # license =
    ##### abstract
    # keywords


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
    #
    # tags = Map(
    #     Delegate(OAIThroughTags),
    #     RunPython(
    #         'force_text',
    #         Concat(
    #             Try(ctx['record']['header']['setSpec']),
    #             Try(ctx['record']['metadata']['dc']['dc:type']),
    #             Try(ctx['record']['metadata']['dc']['dc:format']),
    #             Try(ctx['record']['metadata']['dc']['dc:subject']),
    #         )
    #     )
    # )
    #
    # links = Map(
    #     Delegate(OAIThroughLinks),
    #     RunPython(
    #         'get_links',
    #         Concat(
    #             Try(ctx['record']['metadata']['dc']['dc:identifier']),
    #             Maybe(Maybe(ctx['record'], 'metadata')['dc'], 'dc:relation')
    #         )
    #     )
    # )
    #
    # date_updated = ParseDate(ctx['record']['header']['datestamp'])
    #
    class Extra:
        issn = Try(RunPython('get_issns', ctx.record.metadata.article.front['journal-meta']['issn']))
    #     """
    #     Fields that are combined in the base parser are relisted as singular elements that match
    #     their original entry to preserve raw data structure.
    #     """
    #     # An entity responsible for making contributions to the resource.
    #     contributor = Maybe(Maybe(ctx['record'], 'metadata')['dc'], 'dc:contributor')
    #
    #     # The spatial or temporal topic of the resource, the spatial applicability of the resource,
    #     # or the jurisdiction under which the resource is relevant.
    #     coverage = Maybe(Maybe(ctx['record'], 'metadata')['dc'], 'dc:coverage')
    #
    #     # An entity primarily responsible for making the resource.
    #     creator = Maybe(Maybe(ctx['record'], 'metadata')['dc'], 'dc:creator')
    #
    #     # A point or period of time associated with an event in the lifecycle of the resource.
    #     dates = Maybe(Maybe(ctx['record'], 'metadata')['dc'], 'dc:date')
    #
    #     # The file format, physical medium, or dimensions of the resource.
    #     resource_format = Maybe(Maybe(ctx['record'], 'metadata')['dc'], 'dc:format')
    #
    #     # An unambiguous reference to the resource within a given context.
    #     identifiers = Concat(
    #         Try(ctx['record']['metadata']['dc']['dc:identifier']),
    #         Maybe(ctx['record']['header'], 'identifier')
    #     )
    #
    #     # A related resource.
    #     relation = RunPython('get_relation', ctx)
    #
    #     # A related resource from which the described resource is derived.
    #     source = Maybe(Maybe(ctx['record'], 'metadata')['dc'], 'dc:source')
    #
    #     # The nature or genre of the resource.
    #     resource_type = Try(ctx.record.metadata.dc['dc:type'])
    #
    #     set_spec = Maybe(ctx.record.header, 'setSpec')
    #
    #     # Language also stored in the Extra class in case the language reported cannot be parsed by ParseLanguage
    #     language = Try(ctx.record.metadata.dc['dc:language'])

    def get_issns(self, list_):
        issns = {}
        for item in list_:
            issns[item['@pub-type']] = item['#text']
        return issns

    def get_date(self, list_):
        for item in list_:
            if item['@pub-type'] == 'epub':
                return str(arrow.get(int(item['year']), int(item['month']), int(item['day'])))
