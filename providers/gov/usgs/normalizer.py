from share.normalize import *
from share.normalize.utils import format_doi_as_url


class Person(Parser):
    given_name = Maybe(ctx, 'given')
    family_name = Maybe(ctx, 'family')


class Contributor(Parser):
    order_cited = ctx('index')
    cited_name = Join(Concat(Maybe(ctx, 'given'), Maybe(ctx, 'family')), joiner=' ')
    person = Delegate(Person, ctx)


class Link(Parser):
    url = ctx
    type = RunPython('get_link_type', ctx)

    def get_link_type(self, link):
        if 'dx.doi.org' in link:
            return 'doi'
        if 'usgs.gov' in link:
            return 'provider'
        return 'misc'


class ThroughLinks(Parser):
    link = Delegate(Link, ctx)


class Publisher(Parser):
    name = ctx


class Association(Parser):
    entity = Delegate(Publisher, ctx)


class CreativeWork(Parser):
    title = ctx.title
    description = Maybe(ctx, 'docAbstract')
    date_updated = ParseDate(ctx.lastModifiedDate)
    date_published = ParseDate(ctx.displayToPublicDate)
    language = Maybe(ctx, 'language')
    publishers = Map(Delegate(Association), Maybe(ctx, 'publisher'))
    contributors = Map(Delegate(Contributor), Maybe(Maybe(ctx, 'contributors'), 'authors'))
    links = Map(
        Delegate(ThroughLinks),
        RunPython('format_doi_as_url', Maybe(ctx, 'doi')),
        RunPython('get_links', ctx.links),
        RunPython('format_usgs_id_as_url', ctx.id)
    )

    class Extra:
        additional_online_files = Maybe(ctx, 'additionalOnlineFiles')
        country = Maybe(ctx, 'country')
        defined_type = Maybe(ctx, 'defined_type')
        end_page = Maybe(ctx, 'endPage')
        geographic_extents = Maybe(ctx, 'geographicExtents')
        index_id = Maybe(ctx, 'indexId')
        ipds_id = Maybe(ctx, 'ipdsId')
        issue = Maybe(ctx, 'issue')
        online_only = Maybe(ctx, 'onlineOnly')
        other_geospatial = Maybe(ctx, 'otherGeospatial')
        publication_subtype = Maybe(ctx, 'publicationSubtype')
        publication_year = Maybe(ctx, 'publicationYear')
        start_page = Maybe(ctx, 'startPage')
        state = Maybe(ctx, 'state')
        type = Maybe(ctx, 'type')
        volume = Maybe(ctx, 'volume')

    def format_doi_as_url(self, doi):
        return format_doi_as_url(self, doi)

    def format_usgs_id_as_url(self, id):
        return 'https://pubs.er.usgs.gov/publication/{}'.format(id)

    def get_links(self, links):
        return [link['url'] for link in links if link.get('url')]
